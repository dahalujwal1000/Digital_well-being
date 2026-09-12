"""Real data provider backed by SQLite.

Same interface as mock_data (get_day / last_n_days / summary_line) so the
dashboard needs zero changes. Reuses mock_data's dataclasses + colors.
"""

from datetime import datetime, timedelta

from src.database.db import Store, DB_PATH
from src.core.website_rules import site_color
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


def get_day(day) -> DayStats:
    store = _get_store()
    if store is None:
        raise RuntimeError("no store")
    date_str = day.strftime("%Y-%m-%d")

    stats = DayStats(day=day)
    open_total = 0
    starts, ends = [], []
    now = datetime.now()
    now_sec = now.hour * 3600 + now.minute * 60 + now.second

    for boot, end, reason, active, idle in store.sessions_for_day(date_str):
        start_s = _to_seconds(boot)
        end_s = _to_seconds(end) if end else now_sec
        # sessions are stored under their boot date, so a session opened at
        # 23:50 shows fully on that day. Clamp to the viewed day's clock so
        # the timeline stays inside 00:00-24:00.
        start_c, end_c = max(0, start_s), min(24 * 3600, end_s)
        stats.sessions.append(SessionRow(
            date=date_str, start_sec=start_c,
            end_sec=max(start_c, end_c),
            active_sec=active, idle_sec=idle,
            reason=reason if end else "RUNNING"))
        open_total += max(0, end_c - start_c)
        starts.append(start_c)
        if end:
            ends.append(end_c)
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

    for i, (site, sec) in enumerate(store.web_for_day(date_str)):
        stats.websites.append(AppUsage(name=site, process="web",
                                       color=site_color(site, i),
                                       active_sec=sec))

    if starts:
        stats.first_used_sec = min(starts)
        stats.last_used_sec = max(ends) if ends else now_sec
    return stats


def last_n_days(n: int):
    today = datetime.now().date()
    return [get_day(today - timedelta(days=i)) for i in range(n - 1, -1, -1)]


def summary_line(stats: DayStats) -> str:
    return (f"Laptop open {fmt_hm(stats.open_sec)}  •  "
            f"Idle {fmt_hm(stats.idle_sec)}  •  Unlocks {stats.unlocks}")
