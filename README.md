# Digital Wellbeing (Windows & Linux)

A Digital-Wellbeing-style desktop application:
today's **Active screen time**, **Laptop open time**, **Idle time**, **Unlocks**,
hourly activity chart, top apps/websites, laptop sessions timeline —
tracked by a background engine that lives in the **system tray**, viewed in a
polished dashboard with **animated ring, hover tooltips, click-to-jump week
chart and pull-to-refresh**. Restart-proof by design.

**Platforms Supported:** Windows 10/11 & Linux (Fedora, Ubuntu, Debian, Arch, GNOME, KDE, X11, Wayland).

## Stack
Python 3.11+ · CustomTkinter · SQLite · OS APIs (ctypes / Win32 on Windows; X11 / Wayland / D-Bus on Linux) · PyInstaller

## Run from source (dev)

### Linux (Fedora / Ubuntu / Debian)

1. **Install system dependencies**:
   ```bash
   # Fedora
   sudo dnf install python3-tkinter libayatana-appindicator-gtk3

   # Ubuntu / Debian
   sudo apt install python3-tk gir1.2-ayatanaappindicator3-0.1
   ```

2. **Install Python packages**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run**:
   ```bash
   python3 run_app.py                 # tracker + system tray (normal use)
   python3 run_app.py --dashboard     # open the dashboard window
   python3 run_app.py --no-tray       # headless tracker (testing / CLI)
   ```

### Windows

```powershell
# 1. Install Python 3.11+ (winget install Python.Python.3.12) if needed
# 2. From this folder:
pip install -r requirements.txt
python run_app.py                 # tracker + tray (normal use)
python run_app.py --dashboard     # dashboard window
python smoke_test.py              # opens the UI, auto-closes
```

## Commands & Switches

| Command | What it does |
|---|---|
| `python3 run_app.py` / `DigitalWellbeing.exe` | tracker + system tray (normal use / autostart) |
| `python3 run_app.py --dashboard` / `DigitalWellbeing.exe --dashboard` | open the dashboard window |
| `python3 run_app.py --no-tray` / `DigitalWellbeing.exe --no-tray` | headless tracker (testing) |
| `python3 run_app.py --autostart-status` | show the start-at-logon setting |
| `python3 run_app.py --enable-autostart` | enable start at login |
| `python3 run_app.py --disable-autostart` | disable start at login |

Tray menu: Open Dashboard · Today's active time · Start at Login · Exit.

### Data Storage & Logs
* **Linux**: Data lives in `~/.local/share/digital-wellbeing/wellbeing.db`, logs in `~/.local/share/digital-wellbeing/logs/wellbeing.log`.
* **Windows**: Data lives in `%APPDATA%\DigitalWellbeing\wellbeing.db`, logs in `%APPDATA%\DigitalWellbeing\logs\wellbeing.log`.

## Start at Windows logon

`src/utils/autostart.py` owns this, and only ever installs **one** entry:

| Mechanism | When it is used | Why |
|---|---|---|
| Windows Task Scheduler task `\DigitalWellbeing` | default: the tray toggle, the installer (`--enable-autostart --autostart-mode task`) and `--enable-autostart` all try this first | starts 30s after logon (boot has settled), is never stopped when the laptop runs on battery, has no 72-hour runtime limit and is restarted by Windows if it crashes |
| `HKCU\...\Run` value `DigitalWellbeing` | only if Windows refuses to import the task (policy / locked-down ACL) | needs no admin at all, so "Start with Windows" still works |

Rules that keep it consistent:

* autostart always launches the **silent tracker + tray** - never
  `--dashboard`;
* enabling one mechanism deletes the other, and every tracker start calls
  `autostart.reconcile()` to drop a leftover Run key when the task exists, so a
  logon cannot start two trackers (the single-instance mutex is the backstop);
* `schtasks /create /xml` imports a task for the current user **without**
  elevation (verified on Windows 11; note the switch-based
  `schtasks /create /sc onlogon` form *is* refused unelevated), and if a
  machine still refuses, the tray offers an admin path
  (*Use startup task (admin)*) and the installer does it while elevated;
* uninstalling removes both entries (`--disable-autostart` plus a
  `schtasks /delete` safety net).

Verify by hand:

```powershell
schtasks /query /tn DigitalWellbeing /v /fo LIST                   # task
reg query HKCU\Software\Microsoft\Windows\CurrentVersion\Run /v DigitalWellbeing   # run key
```

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
  tray/tray_app.py          # system tray icon + startup settings
  utils/autostart.py        # start at logon: task XML + Run key fallback
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
   the "start when I log in" on-logon task and a clean uninstaller.
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
8. ✅ Reliable start at logon (v1.3):
   - Task Scheduler "on logon" task: 30s delay, no battery stop, no runtime
     limit, restart-on-failure (registered by the installer / the tray's
     admin action)
   - HKCU Run key fallback so the tray toggle also works without UAC
   - `--enable-autostart` / `--disable-autostart` / `--autostart-status` CLI
   - one autostart entry, always: enabling one mechanism clears the other
9. Unit tests: `python -m unittest discover -s tests`

