"""Real data provider backed by SQLite.

Same interface as mock_data (get_day / last_n_days / summary_line) so the
dashboard needs zero changes. Reuses mock_data's dataclasses + colors.
"""

from datetime import datetime, timedelta

from src.database.db import Store, DB_PATH
from src.dashboard.mock_data import (APP_COLORS, AppUsage, DayStats,
                                     SessionRow)
from src.utils.time_format import fmt_hm

_FALLBACK_COLORS = ["#4fc3f7", "#ffd54f", "#81c784", "#f48fb1", "#b39ddb",
                    "#90caf9", "#a5d6a7", "#ef9a9a", "#ffe082", "#ce93d8"]

_store: Store | None = None


def _get_store() -> Store | None:
    global _store
    if _store is None:
        try:
            _store = Store()
        except Exception:
            return None
    return _store


def available() -> bool:
    return DB_PATH.exists()


def _color_for(exe: str, index: int) -> str:
    return APP_COLORS.get(exe, _FALLBACK_COLORS[index % len(_FALLBACK_COLORS)])


def _to_seconds(iso: str) -> int:
    """ISO datetime -> seconds since midnight of that date."""
    dt = datetime.strptime(iso, "%Y-%m-%d %H:%M:%S")
    return dt.hour * 3600 + dt.minute * 60 + dt.second


def _duration(start: str, end: str | None) -> int:
    """Session open seconds, crossing midnight handled by full timedelta."""
    fmt = "%Y-%m-%d %H:%M:%S"
    s = datetime.strptime(start, fmt)
    e = datetime.strptime(end, fmt) if end else datetime.now()
    return max(0, int((e - s).total_seconds()))


def get_day(day) -> DayStats:
    store = _get_store()
    if store is None:
        raise RuntimeError("no store")
    date_str = day.strftime("%Y-%m-%d")

    stats = DayStats(day=day)
    open_total = 0
    starts, ends = [], []

    for boot, end, reason, active, idle in store.sessions_for_day(date_str):
        now_sec = (datetime.now().hour * 3600 + datetime.now().minute * 60
                   + datetime.now().second)
        stats.sessions.append(SessionRow(
            date=date_str, start_sec=_to_seconds(boot),
            end_sec=_to_seconds(end) if end else now_sec,
            active_sec=active, idle_sec=idle,
            reason=reason if end else "RUNNING"))
        open_total += _duration(boot, end)
        starts.append(_to_seconds(boot))
        if end:
            ends.append(_to_seconds(end))
        stats.active_sec += active

    # open >= active+idle; idle derives from open - active (DayStats property)
    stats.open_sec = max(open_total, stats.active_sec)

    stats.unlocks = store.unlocks_for_day(date_str)
    stats.hourly_active, stats.hourly_idle = store.hourly_for_day(date_str)

    for i, (app_name, _title, sec) in enumerate(store.apps_for_day(date_str)):
        exe = app_name.lower()
        color = _color_for(exe, i)
        stats.apps.append(AppUsage(name=app_name, process=exe, color=color,
                                   active_sec=sec))

    if starts:
        stats.first_used_sec = min(starts)
        stats.last_used_sec = (max(ends) if ends
                               else (datetime.now().hour * 3600
                                     + datetime.now().minute * 60))
    return stats


def last_n_days(n: int):
    today = datetime.now().date()
    return [get_day(today - timedelta(days=i)) for i in range(n - 1, -1, -1)]


def summary_line(stats: DayStats) -> str:
    return (f"Laptop open {fmt_hm(stats.open_sec)}  •  "
            f"Idle {fmt_hm(stats.idle_sec)}  •  Unlocks {stats.unlocks}")
