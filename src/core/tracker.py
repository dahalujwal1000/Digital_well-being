"""Tracking engine v1: foreground app + idle detection -> SQLite.

- Tick every 5s: read foreground window + last-input time.
- Idle > idle_timeout_sec counts as idle (open but not used).
- Flush to SQLite every 15s (crash loses at most 15s).
- Sessions: open on start, close on shutdown/sleep/logoff,
  crash-recovered on next boot.
"""

import logging
import threading
import time
from datetime import datetime

from src.core.power_events import PowerEventWatcher
from src.core.win32_hooks import get_foreground, get_idle_seconds
from src.core.website_rules import is_browser, parse_site
from src.database.db import Store
from src.utils.app_info import friendly_name
from src.utils.log import get_logger

TICK_SEC = 5
FLUSH_SEC = 15
IDLE_TIMEOUT_SEC = 60
MAX_DT_SEC = 30  # cap for clock hiccups / resumed sleep

log = get_logger("tracker")


class Tracker:
    def __init__(self, store: Store | None = None,
                 idle_timeout: int = IDLE_TIMEOUT_SEC):
        self.store = store or Store()
        self.idle_timeout = idle_timeout
        self._stop = threading.Event()
        self._thread = None

        # pending deltas, flushed periodically.
        # GUARD: _tick runs on the tracker thread while _flush() may run on
        # the Win32 message-pump thread (lock/suspend/endsession) -- every
        # access to pending state must hold self._lock.
        self._lock = threading.Lock()
        self._pending_app: dict[tuple, list] = {}   # (date,hour,exe) -> [sec, title]
        self._pending_hourly: dict[tuple, list] = {}  # (date,hour) -> [act, idle]
        self._pending_web: dict[tuple, float] = {}  # (date,hour,site) -> sec
        self._pending_active = 0
        self._pending_idle = 0

        now = datetime.now()
        self.store.recover_crashed(now.strftime("%Y-%m-%d %H:%M:%S"))
        self.session_id = self.store.open_session(
            now.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d %H:%M:%S"))
        self.store.log_event("BOOT")

        self._watcher = PowerEventWatcher({
            "on_lock": self._on_lock,
            "on_unlock": self._on_unlock,
            "on_suspend": self._on_suspend,
            "on_resume": self._on_resume,
            "on_endsession": self._on_endsession,
        })

    # ---------------------------------------------------------- lifecycle --
    @staticmethod
    def _safe_run(fn, *args) -> None:
        """Run a background thread body; log instead of dying silently."""
        try:
            fn(*args)
        except Exception:
            log.exception("background thread crashed (continuing)")

    def start(self) -> None:
        # tracking still works if the event watcher fails; we only lose
        # lock/sleep/shutdown session events (which are logged).
        # The window and its message pump MUST share one thread (Win32
        # message queues are per-thread), so one thread runs _watcher.run().
        threading.Thread(target=self._safe_run, args=(self._watcher.run,),
                         daemon=True).start()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self, reason: str = "SHUTDOWN") -> None:
        # idempotent: endsession + tray Exit can both call stop() -- only the
        # first call closes the session (otherwise end_time is overwritten).
        if self._stop.is_set():
            return
        self._stop.set()
        self._watcher.stop()
        if self._thread:
            self._thread.join(timeout=5)
        self._flush()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.store.close_session(self.session_id, now, reason)
        self.store.log_event(reason)
        self.store.close()
        log.info("tracker stopped (%s), session %s closed", reason,
                 self.session_id)

    def _run(self) -> None:
        last = time.time()
        last_flush = last
        session_date = datetime.now().strftime("%Y-%m-%d")
        while not self._stop.is_set():
            time.sleep(TICK_SEC)
            now = time.time()
            dt = min(now - last, MAX_DT_SEC)
            last = now
            # midnight rollover: pending data is keyed by date, but the open
            # session keeps its boot date. Without this, time tracked after
            # 00:00 is credited to yesterday's session and today shows 0.
            today = datetime.now()
            today_str = today.strftime("%Y-%m-%d")
            if today_str != session_date:
                try:
                    self._flush()
                    self.store.close_session(
                        self.session_id, session_date + " 23:59:59",
                        "MIDNIGHT")
                    self.session_id = self.store.open_session(
                        today_str, today.strftime("%Y-%m-%d 00:00:00"))
                    session_date = today_str
                    log.info("midnight rollover - new session %s",
                             self.session_id)
                except Exception:
                    log.exception("midnight rollover failed (continuing)")
            self._tick(dt)
            if now - last_flush >= FLUSH_SEC:
                last_flush = now
                self._flush()

    # ------------------------------------------------------------- tracking --
    def _tick(self, dt: float) -> None:
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        hour = now.hour

        idle = get_idle_seconds() >= self.idle_timeout
        fg = None if idle else get_foreground()

        with self._lock:
            if fg is not None:
                _, exe, title = fg
                key = (date_str, hour, exe)
                entry = self._pending_app.get(key)
                if entry is None:
                    self._pending_app[key] = entry = [0.0, title]
                entry[0] += dt
                entry[1] = title
                if is_browser(exe):
                    site = parse_site(title)
                    self._pending_web[(date_str, hour, site)] = (
                        self._pending_web.get((date_str, hour, site), 0.0) + dt)
                pend = self._pending_hourly.setdefault(
                    (date_str, hour), [0.0, 0.0])
                pend[0] += dt
                self._pending_active += dt
            else:
                pend = self._pending_hourly.setdefault(
                    (date_str, hour), [0.0, 0.0])
                pend[1] += dt
                self._pending_idle += dt

    # -------------------------------------------------------------- flush --
    def _flush(self) -> None:
        # snapshot-and-clear under the lock, then write to SQLite outside it
        # (the pump thread may call this concurrently with the tracker loop).
        with self._lock:
            if not (self._pending_app or self._pending_hourly
                    or self._pending_active or self._pending_idle):
                return
            app, hourly, web = (self._pending_app, self._pending_hourly,
                                self._pending_web)
            active, idle = self._pending_active, self._pending_idle
            self._pending_app = {}
            self._pending_hourly = {}
            self._pending_web = {}
            self._pending_active = self._pending_idle = 0.0

        try:
            for (date_str, hour, exe), (sec, title) in app.items():
                self.store.add_app_time(date_str, hour, friendly_name(exe),
                                        exe, title, int(sec))
            for (date_str, hour), (act, idle) in hourly.items():
                self.store.add_hourly(date_str, hour, int(act), int(idle))
            for (date_str, hour, site), sec in web.items():
                self.store.add_web_time(date_str, hour, site, int(sec))
            if active or idle:
                self.store.update_session_time(
                    self.session_id, int(active), int(idle))
        except Exception:
            # never lose the whole run because one write failed
            log.exception("flush failed - %d app / %d hourly / %d web rows "
                          "dropped", len(app), len(hourly), len(web))

    # ------------------------------------------------------- event handlers --
    # These run on the Win32 message-pump thread; a crash here would kill
    # lock/sleep/shutdown handling, so each handler is fully guarded.
    def _on_lock(self) -> None:
        try:
            self._flush()
            self.store.log_event("LOCK")
        except Exception:
            log.exception("LOCK handler failed")

    def _on_unlock(self) -> None:
        try:
            self.store.log_event("UNLOCK")
        except Exception:
            log.exception("UNLOCK handler failed")

    def _on_suspend(self) -> None:
        try:
            self._flush()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.store.close_session(self.session_id, now, "SLEEP")
            self.store.log_event("SLEEP")
        except Exception:
            log.exception("SUSPEND handler failed")

    def _on_resume(self) -> None:
        try:
            self.store.log_event("WAKE")
            now = datetime.now()
            self.session_id = self.store.open_session(
                now.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d %H:%M:%S"))
            log.info("resumed - new session %s", self.session_id)
        except Exception:
            log.exception("RESUME handler failed")

    def _on_endsession(self, reason: str = "SHUTDOWN") -> None:
        # Windows is shutting down / user logging off - save NOW
        try:
            self._flush()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.store.close_session(self.session_id, now, reason)
            self.store.log_event(reason)
        except Exception:
            log.exception("%s handler failed", reason)

    # -------------------------------------------------------------- status --
    def _date_str(self) -> str:
        """Today's date key (exposed for tests and status display)."""
        return datetime.now().strftime("%Y-%m-%d")

    def today_totals(self) -> tuple[int, int]:
        """(active_sec, idle_sec) for today across ALL of today's sessions,
        plus unflushed pending deltas.

        Sleep/wake splits the day into several sessions; summing only the
        current session made the tray title drop to 0 after every wake.
        Pending deltas are keyed by date in _tick, so they always belong
        to today."""
        with self._lock:
            pending_active, pending_idle = (self._pending_active,
                                            self._pending_idle)
        active, idle = self.store.day_totals(self._date_str())
        return (active + int(pending_active), idle + int(pending_idle))