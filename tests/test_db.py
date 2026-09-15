"""Unit tests for the SQLite store (no GUI, temp DB)."""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.database.db import Store  # noqa: E402


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.dir.name) / "test.db")

    def tearDown(self):
        self.store.close()
        self.dir.cleanup()

    def test_session_lifecycle(self):
        sid = self.store.open_session("2026-09-13", "2026-09-13 10:00:00")
        row = self.store.get_session(sid)
        self.assertIsNotNone(row)
        self.assertEqual(row[3], "RUNNING")
        self.assertIsNone(row[2])          # end_time NULL while running

        self.store.update_session_time(sid, 120, 30)
        self.store.close_session(sid, "2026-09-13 12:00:00", "SHUTDOWN")
        row = self.store.get_session(sid)
        self.assertEqual(row[2], "2026-09-13 12:00:00")
        self.assertEqual(row[3], "SHUTDOWN")
        self.assertEqual(row[4], 120)      # active
        self.assertEqual(row[5], 30)       # idle

    def test_crash_recovery(self):
        sid = self.store.open_session("2026-09-13", "2026-09-13 10:00:00")
        self.store.update_session_time(sid, 120, 30)
        self.store.recover_crashed("2026-09-13 18:00:00")
        row = self.store.get_session(sid)
        self.assertEqual(row[3], "CRASH")  # open session was closed
        self.assertEqual(row[2], "2026-09-13 10:02:30")  # clamped to boot + tracked

    def test_day_totals_sums_all_sessions(self):
        s1 = self.store.open_session("2026-09-13", "2026-09-13 09:00:00")
        self.store.update_session_time(s1, 100, 20)
        self.store.close_session(s1, "2026-09-13 10:00:00", "SLEEP")

        s2 = self.store.open_session("2026-09-13", "2026-09-13 11:00:00")
        self.store.update_session_time(s2, 50, 10)
        self.store.close_session(s2, "2026-09-13 12:00:00", "SHUTDOWN")

        active, idle = self.store.day_totals("2026-09-13")
        self.assertEqual(active, 150)
        self.assertEqual(idle, 30)

    def test_app_usage_upsert_accumulates(self):
        self.store.add_app_time("2026-09-13", 10, "VS Code", "code.exe",
                                "file.py", 60)
        self.store.add_app_time("2026-09-13", 10, "VS Code", "code.exe",
                                "other.py", 30)
        rows = self.store.apps_for_day("2026-09-13")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][2], 90)   # summed seconds
        self.assertEqual(rows[0][1], "other.py")  # title updated

    def test_hourly_and_web(self):
        self.store.add_hourly("2026-09-13", 10, 100, 50)
        self.store.add_hourly("2026-09-13", 10, 20, 10)
        self.store.add_hourly("2026-09-13", 11, 5, 0)
        active, idle = self.store.hourly_for_day("2026-09-13")
        self.assertEqual(active[10], 120)
        self.assertEqual(idle[10], 60)
        self.assertEqual(active[11], 5)
        self.assertEqual(len(active), 24)  # full 24h vectors

        self.store.add_web_time("2026-09-13", 10, "YouTube", 30)
        self.store.add_web_time("2026-09-13", 11, "YouTube", 45)
        web = dict(self.store.web_for_day("2026-09-13"))
        self.assertEqual(web["YouTube"], 75)

    def test_unlock_count(self):
        self.store.log_event("UNLOCK")
        self.store.log_event("LOCK")
        self.store.log_event("UNLOCK")
        self.assertEqual(self.store.unlocks_for_day("2099-01-01"), 0)

    def test_reconnect_recovers_queries(self):
        # simulate a broken connection; next query must reconnect itself
        self.store._con.close()
        rows = self.store.apps_for_day("2026-09-13")
        self.assertEqual(rows, [])
        # and writes work again afterwards
        self.store.add_app_time("2026-09-13", 10, "Test", "t.exe", "", 5)
        self.assertEqual(len(self.store.apps_for_day("2026-09-13")), 1)


if __name__ == "__main__":
    unittest.main()
