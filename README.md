# Digital Wellbeing for Windows (v1)

A Digital-Wellbeing-style **dashboard** for Windows:
today's **Active screen time**, **Laptop open time**, **Idle time**, **Unlocks**,
hourly activity chart, top apps, and laptop sessions timeline.
Restart-proof by design (each boot is its own session, daily totals are sums).

**v1 scope:** tracking + storage + dashboard UI. NO blocking / task-kill.

## Stack
Python 3.11+ · CustomTkinter · SQLite (later) · Win32 API via ctypes (later)

## Run the dashboard UI (currently with mock data)

```powershell
# 1. Install Python 3.11+ (winget install Python.Python.3.12) if needed
# 2. From this folder:
pip install -r requirements.txt
python run_dashboard.py
```

## Structure
```
run_dashboard.py          # open the dashboard
src/
  dashboard/app.py        # main window + date navigation
  dashboard/home_tab.py   # ring, stat cards, hourly chart
  dashboard/apps_tab.py   # top apps list
  dashboard/sessions_tab.py  # laptop sessions timeline
  dashboard/mock_data.py  # data provider (swap with SQLite later)
  dashboard/widgets/      # TimeRing, HourlyBarChart, AppRow
  utils/time_format.py
```

## Data provider contract
The UI only talks to `mock_data.get_day(date)` / `last_n_days(n)`.
The real tracker will implement the same functions backed by SQLite
(`sessions`, `app_usage`, `events` tables) — no UI changes needed.

## Roadmap
1. ✅ Dashboard UI
2. ✅ Win32 tracker (`GetForegroundWindow`, `GetLastInputInfo`, power events)
3. ✅ SQLite storage (WAL, flush every 15s, crash recovery)
4. ✅ System tray + autostart
5. ✅ Multi-day views, per-website tracking
6. ✅ Hardening pass (v1.1):
   - thread-safe tracker (tick vs. flush on different threads now locked)
   - idempotent `stop()` (no double session close on shutdown + exit)
   - rotating file logging -> `%APPDATA%\DigitalWellbeing\logs\wellbeing.log`
   - SQLite auto-reconnect on locked/closed connections
   - midnight-clamped session timelines, empty-state UI, wheel-scroll fix
   - unit tests: `python -m unittest discover -s tests`

## Run the tracker (background, system tray)

```powershell
python run_tracker.py              # tray + tracking (normal use)
python run_tracker.py --no-tray    # headless
python run_tracker.py --duration N # test run for N seconds
```

Tray menu: Open Dashboard · Today's active time · Start with Windows · Exit.

Data lives in `%APPDATA%\DigitalWellbeing\wellbeing.db` (SQLite, WAL).
