# Digital Wellbeing for Windows (v1.2)

A Digital-Wellbeing-style **single Windows app**:
today's **Active screen time**, **Laptop open time**, **Idle time**, **Unlocks**,
hourly activity chart, top apps/websites, laptop sessions timeline —
tracked by a background engine that lives in the **system tray**, viewed in a
polished dashboard with **animated ring, hover tooltips, click-to-jump week
chart and pull-to-refresh**. Restart-proof by design.

**v1 scope:** tracking + storage + dashboard UI. NO blocking / task-kill.

## Stack
Python 3.11+ · CustomTkinter · SQLite · Win32 API via ctypes · PyInstaller

## Run from source (dev)

```powershell
# 1. Install Python 3.11+ (winget install Python.Python.3.12) if needed
# 2. From this folder:
pip install -r requirements.txt
python run_app.py                 # tracker + tray (normal use)
python run_app.py --dashboard     # dashboard window
python smoke_test.py              # opens the UI, auto-closes
```

## The ONE executable

The whole product ships as a single exe:

| Command | What it does |
|---|---|
| `DigitalWellbeing.exe` | tracker + system tray (normal use / autostart) |
| `DigitalWellbeing.exe --dashboard` | open the dashboard window |
| `DigitalWellbeing.exe --no-tray` | headless tracker (testing) |

Tray menu: Open Dashboard · Today's active time · Start with Windows · Exit.

Data lives in `%APPDATA%\DigitalWellbeing\wellbeing.db` (SQLite, WAL),
logs in `%APPDATA%\DigitalWellbeing\logs\wellbeing.log`.

## Structure
```
run_app.py                  # THE entry point (tracker/tray or --dashboard)
src/
  core/tracker.py           # Win32 tracking engine
  dashboard/app.py          # main window + date navigation + DPI aware
  dashboard/home_tab.py     # animated ring, stat cards, hourly chart
  dashboard/apps_tab.py     # top apps/websites (hover-highlight rows)
  dashboard/sessions_tab.py # laptop sessions timeline
  dashboard/week_tab.py     # last 7 days (hover + click bar to open that day)
  dashboard/widgets/        # TimeRing, HourlyBarChart, AppRow, PullRefresher…
  database/                 # SQLite provider (WAL, flush, auto-reconnect)
  tray/tray_app.py          # system tray icon + autostart toggle
installer.iss               # Inno Setup installer script (free)
```

## Publish pipeline (free)

1. **Build** the exe (Windows only):
   ```powershell
   .\build_exe.bat        # -> dist\DigitalWellbeing\DigitalWellbeing.exe
   ```
   Uses `--onedir` (folder output): starts faster and is far less likely to be
   flagged by antivirus than onefile self-extracting exes.
2. **Installer** (free): compile `installer.iss` with
   [Inno Setup](https://jrsoftware.org/isinfo.php) →
   `Output\DigitalWellbeing-Setup.exe`. Includes Start Menu/desktop shortcuts,
   an optional "start when I log in" task and a clean uninstaller.
3. **Avoid the "virus" flag** (free route):
   - Distribute via GitHub Releases (reputable HTTPS domain).
   - Submit the built exe to Microsoft as a false-positive/whitelist request:
     https://www.microsoft.com/en-us/wdsi/filesubmission
   - Add icon + version metadata to the exe before wide distribution.
   - Expect SmartScreen "More info → Run anyway" for the first few weeks
     until reputation builds. Keep the built file hash stable (rebuild rarely).
   - Free SmartScreen-trusted signing alternative: Azure Trusted Signing
     (~$10/mo) if you want to skip the reputation wait.

## Roadmap
1. ✅ Dashboard UI
2. ✅ Win32 tracker (`GetForegroundWindow`, `GetLastInputInfo`, power events)
3. ✅ SQLite storage (WAL, flush every 15s, crash recovery)
4. ✅ System tray + autostart
5. ✅ Multi-day views, per-website tracking
6. ✅ Hardening pass (v1.1)
7. ✅ Polish pass (v1.2):
   - animated progress ring (ease-out sweep)
   - hover tooltips on hourly chart + week chart
   - click a week bar to open that day
   - hover highlights on app rows and session cards
   - per-monitor DPI awareness, centered window
   - keyboard: ← / → change day, Home = today, F5 refresh, Esc close
   - single-exe build (onedir) + Inno Setup installer script
8. Unit tests: `python -m unittest discover -s tests`

