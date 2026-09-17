"""Unit tests for Tracker tick/flush logic (Win32 calls are stubbed)."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import src.core.tracker as tracker_mod  # noqa: E402
from src.core.tracker import Tracker  # noqa: E402
from src.database.db import Store  # noqa: E402

try:                                    # python -m unittest tests.test_tracker
    from . import _quiet              # noqa: F401,E402 - keeps the app log clean
except ImportError:                     # python -m unittest discover -s tests
    import _quiet                     # noqa: F401,E402


class TrackerTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.dir.name) / "test.db")
        self.tracker = Tracker(store=self.store)
        # stop the background machinery - we drive _tick manually
        self.tracker._stop.set()

    def tearDown(self):
        self.tracker._stop.set()
        self.store.close()
        self.dir.cleanup()

    def test_active_tick_accumulates(self):
        tracker_mod.get_idle_seconds = lambda: 0.0          # active
        tracker_mod.get_foreground = lambda: (1, "Code.exe", "VS Code")
        self.tracker._tick(10.0)
        active, _ = self.tracker.today_totals()
        self.assertEqual(active, 10)

    def test_idle_tick_accumulates(self):
        tracker_mod.get_idle_seconds = lambda: 999.0        # > timeout -> idle
        self.tracker._tick(7.0)
        _, idle = self.tracker.today_totals()
        self.assertEqual(idle, 7)

    def test_multi_session_today_totals(self):
        """today_totals must include active time from previous sessions of today."""
        self.tracker._pending_active = 100
        self.tracker._flush()
        now_str = self.tracker._date_str()
        self.tracker.session_id = self.store.open_session(now_str, f"{now_str} 14:00:00")
        self.tracker._pending_active = 50
        active, _ = self.tracker.today_totals()
        self.assertEqual(active, 150)

    def test_flush_persists_everything(self):
        tracker_mod.get_idle_seconds = lambda: 0.0
        tracker_mod.get_foreground = lambda: (1, "chrome.exe",
                                              "Cat video - YouTube")
        self.tracker._tick(12.0)
        self.tracker._tick(8.0)
        self.tracker._flush()

        date_str = self.tracker._date_str()
        apps = dict((r[0], r[2]) for r in self.store.apps_for_day(date_str))
        self.assertEqual(apps.get("Chrome"), 20)
        active, idle = self.store.hourly_for_day(date_str)
        self.assertEqual(sum(active), 20)
        web = dict(self.store.web_for_day(date_str))
        self.assertEqual(web.get("YouTube"), 20)

        # flush clears pending state
        with self.tracker._lock:
            self.assertEqual(self.tracker._pending_app, {})
            self.assertEqual(self.tracker._pending_active, 0)

    def test_stop_is_idempotent(self):
        self.tracker._stop.clear()   # allow one real stop
        self.tracker._thread = None
        self.tracker.stop("SHUTDOWN")
        sid = self.tracker.session_id
        self.tracker.stop("SHUTDOWN")    # second call: no-op, must not raise
        self.assertEqual(self.tracker.session_id, sid)

    def test_threaded_ticks_vs_flush(self):
        """Smoke the lock: many ticks + concurrent flushes must not raise."""
        import threading
        tracker_mod.get_idle_seconds = lambda: 0.0
        tracker_mod.get_foreground = lambda: (1, "Code.exe", "x")

        def hammer():
            for _ in range(200):
                self.tracker._tick(0.1)

        def flusher():
            for _ in range(100):
                self.tracker._flush()

        t1 = threading.Thread(target=hammer)
        t2 = threading.Thread(target=flusher)
        t1.start(); t2.start()
        t1.join(); t2.join()
        self.tracker._flush()
        date_str = self.tracker._date_str()
        apps = dict((r[0], r[2]) for r in self.store.apps_for_day(date_str))
        self.assertEqual(apps.get("VS Code"), 20)   # 200 * 0.1

    def test_duplicate_resume_opens_only_one_session(self):
        self.tracker._on_suspend()
        self.tracker._on_resume()
        resumed_sid = self.tracker.session_id
        self.tracker._on_resume()

        rows = self.store._query(
            "SELECT id, end_reason FROM sessions ORDER BY id")
        running = [sid for sid, reason in rows if reason == "RUNNING"]
        self.assertEqual(running, [resumed_sid])

    def test_resume_refreshes_session_date_after_midnight(self):
        self.tracker._session_date = "1999-12-31"
        self.tracker._on_suspend()
        self.tracker._on_resume()
        self.assertEqual(
            self.tracker._session_date, self.tracker._date_str())

    def test_suspend_prevents_ticks(self):
        tracker_mod.get_idle_seconds = lambda: 0.0
        tracker_mod.get_foreground = lambda: (1, "Code.exe", "x")
        self.tracker._on_suspend()
        self.tracker._tick(10)
        self.assertEqual(self.tracker.today_totals(), (0, 0))

    def test_failed_flush_keeps_pending_data_for_retry(self):
        tracker_mod.get_idle_seconds = lambda: 0.0
        tracker_mod.get_foreground = lambda: (1, "Code.exe", "x")
        self.tracker._tick(10)

        with mock.patch.object(
                self.store, "apply_flush", side_effect=RuntimeError("disk")):
            self.tracker._flush()
        self.assertEqual(self.tracker.today_totals()[0], 10)

        self.tracker._flush()
        self.assertEqual(
            self.store.day_totals(self.tracker._date_str())[0], 10)


if __name__ == "__main__":
    unittest.main()
