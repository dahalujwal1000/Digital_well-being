"""Tracking engine v1: foreground app + idle detection -> SQLite.

- Tick every 5s: read foreground window + last-input time.
- Idle > idle_timeout_sec counts as idle (open but not used).
- Flush to SQLite every 15s (crash loses at most 15s).
- Sessions: open on start, close on shutdown/sleep/logoff,
  crash-recovered on next boot.
"""

import threading
import time
from datetime import datetime

from src.core.power_events import PowerEventWatcher
from src.core.win32_hooks import get_foreground, get_idle_seconds
from src.database.db import Store
from src.utils.app_info import friendly_name

TICK_SEC = 5
FLUSH_SEC = 15
IDLE_TIMEOUT_SEC = 60
MAX_DT_SEC = 30  # cap for clock hiccups / resumed sleep


class Tracker:
    def __init__(self, store: Store | None = None,
                 idle_timeout: int = IDLE_TIMEOUT_SEC):
        self.store = store or Store()
        self.idle_timeout = idle_timeout
        self._stop = threading.Event()
        self._thread = None

        # pending deltas, flushed periodically
        self._pending_app: dict[tuple, list] = {}   # (date,hour,exe) -> [sec, title]
        self._pending_hourly: dict[tuple, list] = {}  # (date,hour) -> [act, idle]
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
    def start(self) -> None:
        threading.Thread(target=self._watcher.start, daemon=True).start()
        threading.Thread(target=self._watcher.pump, daemon=True).start()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self, reason: str = "SHUTDOWN") -> None:
        self._stop.set()
        self._watcher.stop()
        if self._thread:
            self._thread.join(timeout=5)
        self._flush()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.store.close_session(self.session_id, now, reason)
        self.store.log_event(reason)
        self.store.close()

    def _run(self) -> None:
        last = time.time()
        last_flush = last
        while not self._stop.is_set():
            time.sleep(TICK_SEC)
            now = time.time()
            dt = min(now - last, MAX_DT_SEC)
            last = now
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

        if fg is not None:
            _, exe, title = fg
            key = (date_str, hour, exe)
            entry = self._pending_app.get(key)
            if entry is None:
                self._pending_app[key] = entry = [0.0, title]
            entry[0] += dt
            entry[1] = title
            pend = self._pending_hourly.setdefault((date_str, hour), [0.0, 0.0])
            pend[0] += dt
            self._pending_active += dt
        else:
            pend = self._pending_hourly.setdefault((date_str, hour), [0.0, 0.0])
            pend[1] += dt
            self._pending_idle += dt

    # -------------------------------------------------------------- flush --
    def _flush(self) -> None:
        if not (self._pending_app or self._pending_hourly
                or self._pending_active or self._pending_idle):
            return
        for (date_str, hour, exe), (sec, title) in self._pending_app.items():
            self.store.add_app_time(date_str, hour, friendly_name(exe),
                                    exe, title, int(sec))
        for (date_str, hour), (act, idle) in self._pending_hourly.items():
            self.store.add_hourly(date_str, hour, int(act), int(idle))
        if self._pending_active or self._pending_idle:
            self.store.update_session_time(
                self.session_id, int(self._pending_active),
                int(self._pending_idle))
        self._pending_app.clear()
        self._pending_hourly.clear()
        self._pending_active = self._pending_idle = 0.0

    # ------------------------------------------------------- event handlers --
    def _on_lock(self) -> None:
        self._flush()
        self.store.log_event("LOCK")

    def _on_unlock(self) -> None:
        self.store.log_event("UNLOCK")

    def _on_suspend(self) -> None:
        self._flush()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.store.close_session(self.session_id, now, "SLEEP")
        self.store.log_event("SLEEP")

    def _on_resume(self) -> None:
        self.store.log_event("WAKE")
        now = datetime.now()
        self.session_id = self.store.open_session(
            now.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d %H:%M:%S"))

    def _on_endsession(self, reason: str = "SHUTDOWN") -> None:
        # Windows is shutting down / user logging off - save NOW
        self._flush()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.store.close_session(self.session_id, now, reason)
        self.store.log_event(reason)

    # -------------------------------------------------------------- status --
    def today_totals(self) -> tuple[int, int]:
        """(active_sec, idle_sec) including unflushed pending deltas."""
        row = self.store.get_session(self.session_id)
        active = row[4] if row else 0
        idle = row[5] if row else 0
        return (active + int(self._pending_active),
                idle + int(self._pending_idle))