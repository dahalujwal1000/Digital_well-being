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
        self._lifecycle_lock = threading.RLock()
        self._flush_lock = threading.Lock()
        self._clock_reset = threading.Event()
        self._suspended = False
        self._pending_app: dict[tuple, list] = {}   # (date,hour,exe) -> [sec, title]
        self._pending_hourly: dict[tuple, list] = {}  # (date,hour) -> [act, idle]
        self._pending_web: dict[tuple, float] = {}  # (date,hour,site) -> sec
        self._pending_active = 0
        self._pending_idle = 0

        now = datetime.now()
        self.store.recover_crashed(now.strftime("%Y-%m-%d %H:%M:%S"))
        self.session_id = self.store.open_session(
            now.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d %H:%M:%S"))
        self._session_date = now.strftime("%Y-%m-%d")
        self._session_open = True
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
        with self._lifecycle_lock:
            if self._stop.is_set():
                return
            self._stop.set()
        self._watcher.stop()
        if self._thread:
            self._thread.join(timeout=5)
        with self._lifecycle_lock:
            self._flush()
            if self._session_open:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.store.close_session(self.session_id, now, reason)
                self._session_open = False
            self.store.log_event(reason)
            self.store.close()
        log.info("tracker stopped (%s), session %s closed", reason,
                 self.session_id)

    def _run(self) -> None:
        last = time.monotonic()
        last_flush = last
        while not self._stop.wait(TICK_SEC):
            now = time.monotonic()
            if self._clock_reset.is_set():
                self._clock_reset.clear()
                last = last_flush = now
                continue
            dt = max(0.0, min(now - last, MAX_DT_SEC))
            last = now
            # midnight rollover: pending data is keyed by date, but the open
            # session keeps its boot date. Without this, time tracked after
            # 00:00 is credited to yesterday's session and today shows 0.
            today = datetime.now()
            today_str = today.strftime("%Y-%m-%d")
            with self._lifecycle_lock:
                if self._suspended:
                    continue
                if today_str != self._session_date:
                    try:
                        self._flush()
                        if self._session_open:
                            self.store.close_session(
                                self.session_id,
                                self._session_date + " 23:59:59",
                                "MIDNIGHT")
                        self.session_id = self.store.open_session(
                            today_str, today.strftime("%Y-%m-%d 00:00:00"))
                        self._session_date = today_str
                        self._session_open = True
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
        with self._lifecycle_lock:
            if self._suspended or not self._session_open:
                return
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
                            self._pending_web.get(
                                (date_str, hour, site), 0.0) + dt)
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
        with self._lifecycle_lock, self._flush_lock:
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

            app_rows = [
                (date_str, hour, friendly_name(exe), exe, title, int(sec))
                for (date_str, hour, exe), (sec, title) in app.items()
                if int(sec)
            ]
            hourly_rows = [
                (date_str, hour, int(act), int(idle_sec))
                for (date_str, hour), (act, idle_sec) in hourly.items()
                if int(act) or int(idle_sec)
            ]
            web_rows = [
                (date_str, hour, site, int(sec))
                for (date_str, hour, site), sec in web.items()
                if int(sec)
            ]
            try:
                self.store.apply_flush(
                    self.session_id, app_rows, hourly_rows, web_rows,
                    int(active), int(idle))
            except Exception:
                self._restore_pending(app, hourly, web, active, idle)
                log.exception("flush failed - pending data retained for retry")
                return

            residual_app = {
                key: [value[0] - int(value[0]), value[1]]
                for key, value in app.items()
                if value[0] - int(value[0])
            }
            residual_hourly = {
                key: [value[0] - int(value[0]),
                      value[1] - int(value[1])]
                for key, value in hourly.items()
                if value[0] - int(value[0]) or value[1] - int(value[1])
            }
            residual_web = {
                key: value - int(value)
                for key, value in web.items() if value - int(value)
            }
            self._restore_pending(
                residual_app, residual_hourly, residual_web,
                active - int(active), idle - int(idle))

    def _restore_pending(self, app: dict, hourly: dict, web: dict,
                         active: float, idle: float) -> None:
        """Merge a failed snapshot or fractional residual back into memory."""
        with self._lock:
            for key, (sec, title) in app.items():
                current = self._pending_app.get(key)
                if current is None:
                    self._pending_app[key] = [sec, title]
                else:
                    current[0] += sec
            for key, (act, idle_sec) in hourly.items():
                current = self._pending_hourly.setdefault(key, [0.0, 0.0])
                current[0] += act
                current[1] += idle_sec
            for key, sec in web.items():
                self._pending_web[key] = self._pending_web.get(key, 0.0) + sec
            self._pending_active += active
            self._pending_idle += idle

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
            with self._lifecycle_lock:
                if self._suspended:
                    return
                self._suspended = True
                self._clock_reset.set()
                self._flush()
                if self._session_open:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.store.close_session(self.session_id, now, "SLEEP")
                    self._session_open = False
                self.store.log_event("SLEEP")
        except Exception:
            log.exception("SUSPEND handler failed")

    def _on_resume(self) -> None:
        try:
            with self._lifecycle_lock:
                if not self._suspended:
                    return
                now = datetime.now()
                today = now.strftime("%Y-%m-%d")
                self.session_id = self.store.open_session(
                    today, now.strftime("%Y-%m-%d %H:%M:%S"))
                self._session_date = today
                self._session_open = True
                self._suspended = False
                self._clock_reset.set()
                self.store.log_event("WAKE")
                log.info("resumed - new session %s", self.session_id)
        except Exception:
            log.exception("RESUME handler failed")

    def _on_endsession(self, reason: str = "SHUTDOWN") -> None:
        # Windows is shutting down / user logging off - save NOW
        try:
            with self._lifecycle_lock:
                self._suspended = True
                self._clock_reset.set()
                self._flush()
                if self._session_open:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.store.close_session(self.session_id, now, reason)
                    self._session_open = False
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
