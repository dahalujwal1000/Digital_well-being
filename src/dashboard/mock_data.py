"""Mock data layer for the v1 dashboard UI.

The dashboard reads ONLY from this provider (no direct SQL anywhere in the UI).
Later, swap MockDataProvider for the real SQLite provider -- the dashboard code
does not need to change, because both expose the same interface.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta

from src.utils.time_format import fmt_hm


@dataclass
class AppUsage:
    name: str            # friendly name, e.g. "VS Code"
    process: str         # exe name, e.g. "Code.exe"
    color: str           # accent color for the row bar
    active_sec: int


@dataclass
class SessionRow:
    date: str            # '2026-09-12'
    start_sec: int       # seconds since midnight
    end_sec: int
    active_sec: int
    idle_sec: int
    reason: str          # SHUTDOWN / RESTART / SLEEP / CRASH / RUNNING


@dataclass
class DayStats:
    day: date
    active_sec: int = 0
    open_sec: int = 0
    unlocks: int = 0
    first_used_sec: int | None = None
    last_used_sec: int | None = None
    hourly_active: list = field(default_factory=list)   # 24 values, seconds per hour
    hourly_idle: list = field(default_factory=list)
    apps: list = field(default_factory=list)            # list[AppUsage]
    websites: list = field(default_factory=list)        # list[AppUsage] (site slices)
    sessions: list = field(default_factory=list)        # list[SessionRow]

    @property
    def idle_sec(self) -> int:
        return max(0, self.open_sec - self.active_sec)


# ---------------------------------------------------------------- colors ---
APP_COLORS = {
    "Code.exe": "#4fc3f7",
    "chrome.exe": "#ffd54f",
    "Spotify.exe": "#81c784",
    "msedge.exe": "#f48fb1",
    "Discord.exe": "#b39ddb",
    "explorer.exe": "#90caf9",
    "Steam.exe": "#a5d6a7",
    "WINWORD.EXE": "#ef9a9a",
}


# ------------------------------------------------------------ generation ---
def _make_apps(active_sec: int) -> list[AppUsage]:
    """Split total active time across apps with realistic proportions."""
    shares = [("Code.exe", "VS Code", 0.38), ("chrome.exe", "Chrome", 0.27),
              ("Spotify.exe", "Spotify", 0.13), ("msedge.exe", "Edge", 0.09),
              ("Discord.exe", "Discord", 0.07), ("explorer.exe", "Explorer", 0.06)]
    return [AppUsage(name=fname, process=proc, color=APP_COLORS[proc],
                     active_sec=int(active_sec * share))
            for proc, fname, share in shares]


def _make_hourly(active_sec: int) -> tuple[list, list]:
    """Distribute activity across 7a-11p with a lunch dip."""
    weights = {h: (0.0 if h < 7 else 0.6 if 13 <= h <= 14 else 1.0 if 7 <= h <= 22 else 0.2)
               for h in range(24)}
    total_w = sum(weights.values())
    active = [int(active_sec * w / total_w) for w in weights.values()]
    # idle: open-but-not-typing time, larger outside working hours
    idle = [int(a * (0.5 if 13 <= h <= 14 or h > 21 else 0.2)) for h, a in enumerate(active)]
    return active, idle


def _make_sessions(day: date, active_sec: int, idle_sec: int) -> list[SessionRow]:
    chunks = [(9 * 3600 + 2 * 60, 12 * 3600 + 35 * 60, "RESTART", 0.42),
              (13 * 3600 + 5 * 60, 17 * 3600 + 40 * 60, "SHUTDOWN", 0.58)]
    rows = []
    for start, end, reason, share in chunks:
        a = int(active_sec * share)
        i = int(idle_sec * share)
        rows.append(SessionRow(day.isoformat(), start, end, a, i, reason))
    return rows


def get_day(day: date) -> DayStats:
    """Deterministic pseudo-data per date, so switching dates feels real."""
    seed = day.day + day.month
    active = int((4 * 3600 + seed * 240) % (7 * 3600) + 3600)
    idle = int(active * 0.25)
    open_t = active + idle
    hourly_active, hourly_idle = _make_hourly(active)
    used = [h for h, v in enumerate(hourly_active) if v > 0]
    return DayStats(
        day=day,
        active_sec=active,
        open_sec=open_t,
        unlocks=6 + seed % 9,
        first_used_sec=used[0] * 3600 if used else None,
        last_used_sec=(used[-1] + 1) * 3600 if used else None,
        hourly_active=hourly_active,
        hourly_idle=hourly_idle,
        apps=_make_apps(active),
        sessions=_make_sessions(day, active, idle),
    )


def last_n_days(n: int) -> list[DayStats]:
    today = date.today()
    return [get_day(today - timedelta(days=i)) for i in range(n - 1, -1, -1)]


def summary_line(stats: DayStats) -> str:
    return (f"Laptop open {fmt_hm(stats.open_sec)}  •  "
            f"Idle {fmt_hm(stats.idle_sec)}  •  Unlocks {stats.unlocks}")
