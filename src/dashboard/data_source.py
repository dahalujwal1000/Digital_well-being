"""Data source dispatcher: real SQLite when available, mock otherwise."""

from src.dashboard import mock_data


def _real():
    try:
        from src.database import provider
        if provider.available():
            return provider
    except Exception:
        pass
    return None


def get_day(day):
    p = _real()
    try:
        return p.get_day(day) if p else mock_data.get_day(day)
    except Exception:
        return mock_data.get_day(day)


def last_n_days(n):
    p = _real()
    if p:
        try:
            return p.last_n_days(n)
        except Exception:
            pass
    return mock_data.last_n_days(n)


def summary_line(stats):
    return mock_data.summary_line(stats)
