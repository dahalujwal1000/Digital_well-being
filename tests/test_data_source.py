"""Regression tests for dashboard provider selection."""

import sys
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dashboard import data_source, mock_data  # noqa: E402
from src.dashboard import app as dashboard_app  # noqa: E402
from src.database import provider  # noqa: E402


class DataSourceTests(unittest.TestCase):
    def test_missing_database_uses_demo_data(self):
        data_source._mock_warned = False
        with mock.patch.object(data_source, "_real", return_value=None):
            stats = data_source.get_day(date(2026, 9, 17))
        self.assertIsInstance(stats, mock_data.DayStats)
        self.assertEqual(data_source.mode(), "mock")

    def test_real_app_color_matches_case_insensitively(self):
        self.assertEqual(provider._color_for("CODE.EXE", 0),
                         mock_data.APP_COLORS["Code.exe"])

    def test_overnight_dashboard_advances_today(self):
        old_day = date(2026, 9, 17)
        new_day = date(2026, 9, 18)
        state = SimpleNamespace(today=old_day, view_date=old_day)

        class CurrentDate:
            @classmethod
            def today(cls):
                return new_day

        with mock.patch.object(dashboard_app, "date", CurrentDate):
            changed = dashboard_app.DigitalWellbeingApp._sync_today(state)
        self.assertTrue(changed)
        self.assertEqual(state.today, new_day)
        self.assertEqual(state.view_date, new_day)


if __name__ == "__main__":
    unittest.main()
