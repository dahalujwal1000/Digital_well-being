"""Data source dispatcher: real SQLite when available, mock otherwise.

A missing/empty DB is normal (tracker not run yet) -> mock fallback.
Any other exception is a real bug -> log it loudly AND fall back, so the
UI still works but the error is visible in %APPDATA%\\DigitalWellbeing\\logs.
"""

import logging

from src.dashboard import mock_data

log = logging.getLogger("wellbeing.data_source")


def _real():
    try:
        from src.database import provider
        if provider.available():
            return provider
    except Exception:
        log.exception("failed to load SQLite provider")
    return None


def get_day(day):
    p = _real()
    if p:
        try:
            return p.get_day(day)
        except Exception:
            log.exception("provider.get_day(%s) failed - using mock", day)
    else:
        log.info("no SQLite DB - serving mock data for %s", day)
    return mock_data.get_day(day)


def last_n_days(n):
    p = _real()
    if p:
        try:
            return p.last_n_days(n)
        except Exception:
            log.exception("provider.last_n_days(%d) failed - using mock", n)
    return mock_data.last_n_days(n)


def summary_line(stats):
    return mock_data.summary_line(stats)
