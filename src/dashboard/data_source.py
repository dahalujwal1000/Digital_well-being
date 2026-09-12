"""Data source dispatcher: real SQLite when available, mock otherwise.

A missing/empty DB is normal (tracker not run yet) -> mock fallback.
Any other exception is a real bug -> log it loudly AND fall back, so the
UI still works but the error is visible in %APPDATA%\\DigitalWellbeing\\logs.
"""

import logging

from src.dashboard import mock_data

log = logging.getLogger("wellbeing.data_source")

_mode = "mock"   # "real" when the last get_day/last_n_days came from SQLite
_mock_warned = False


def mode() -> str:
    """'real' if the last data fetch hit SQLite, 'mock' for demo data."""
    return _mode


def _real():
    try:
        from src.database import provider
        if provider.available():
            return provider
    except Exception:
        log.exception("failed to load SQLite provider")
    return None


def get_day(day):
    global _mode
    p = _real()
    if p:
        try:
            stats = p.get_day(day)
            _mode = "real"
            return stats
        except Exception:
            log.exception("provider.get_day(%s) failed - using mock", day)
    elif not _mock_warned:
        log.info("no SQLite DB - serving demo data until the tracker runs")
        _mock_warned = True
    _mode = "mock"
    return mock_data.get_day(day)


def last_n_days(n):
    global _mode
    p = _real()
    if p:
        try:
            days = p.last_n_days(n)
            _mode = "real"
            return days
        except Exception:
            log.exception("provider.last_n_days(%d) failed - using mock", n)
    _mode = "mock"
    return mock_data.last_n_days(n)


def summary_line(stats):
    return mock_data.summary_line(stats)
