"""Digital Wellbeing - single application entry point.

The whole product ships as ONE executable. The same binary starts either
the background tracker (system tray) or the dashboard window:

    DigitalWellbeing.exe                # tracker + system tray (normal use / autostart)
    DigitalWellbeing.exe --dashboard    # open the dashboard window
    DigitalWellbeing.exe --no-tray      # headless tracker, Ctrl+C to stop (testing)
    DigitalWellbeing.exe --duration N   # headless tracker for N seconds (testing)
    DigitalWellbeing.exe --autostart-status        # show the startup setting
    DigitalWellbeing.exe --enable-autostart        # start at logon (auto mechanism)
    DigitalWellbeing.exe --disable-autostart       # stop starting at logon

For development you can run the same thing from source:

    python run_app.py                 # same as the first line above
    python run_app.py --dashboard     # same as --dashboard above

Autostart mechanics (see src/utils/autostart.py): an on-logon Task Scheduler
task is preferred and needs an administrator process, so pass
``--enable-autostart --autostart-mode task`` from an elevated prompt (the
installer does exactly that). Without admin rights the same switch falls back
to the per-user HKCU Run key, so "Start with Windows" always works.
"""

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils.log import get_logger  # noqa: E402

log = get_logger("main")


_PLATFORM_LOCK = None


def _acquire_single_instance() -> None:
    """One tracker per user session: a second instance would double-count
    time and contend on the SQLite file."""
    global _PLATFORM_LOCK
    from src.platform import get_lock

    _PLATFORM_LOCK = get_lock()
    if not _PLATFORM_LOCK.acquire():
        log.info("another tracker instance is running - exiting")
        print("Digital Wellbeing tracker is already running.")
        sys.exit(0)


def _run_tracker(args: argparse.Namespace) -> None:
    """Start the background tracking engine (optionally with the tray icon)."""
    _acquire_single_instance()
    from src.core.tracker import Tracker
    from src.utils import autostart

    # exactly one autostart entry: if a logon task was added next to an older
    # Run key value, drop the Run key (the single-instance mutex is the
    # backstop, this keeps the log clean)
    if sys.platform == "win32":
        autostart.reconcile()

    try:
        tracker = Tracker()
        tracker.start()
        log.info("tracker running (session %s), DB: %s",
                 tracker.session_id, tracker.store.path)
        print(f"Tracker running (session {tracker.session_id}). "
              f"DB: {tracker.store.path}")
    except Exception:
        log.exception("failed to start tracker")
        print("Failed to start tracker - see "
              "%APPDATA%\\DigitalWellbeing\\logs\\wellbeing.log")
        sys.exit(1)

    if args.duration:
        time.sleep(args.duration)
        tracker.stop()
        print("Tracker stopped cleanly.")
    elif args.no_tray:
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            tracker.stop()
            print("Tracker stopped cleanly.")
    else:
        try:
            from src.tray.tray_app import TrayApp
            TrayApp(tracker).run()
        except ImportError:
            log.warning("System tray library 'pystray' not available. Running headless.")
            print("System tray library not installed. Running in headless mode (Ctrl+C to stop)...")
            try:
                while True:
                    time.sleep(3600)
            except KeyboardInterrupt:
                tracker.stop()
                print("Tracker stopped cleanly.")


def _run_dashboard() -> None:
    """Open the dashboard window (blocks until the window closes)."""
    from src.dashboard.app import DigitalWellbeingApp

    app = DigitalWellbeingApp()
    app.mainloop()


def _run_autostart_command(args: argparse.Namespace) -> None:
    """Handle the autostart switches and exit."""
    from src.platform import get_autostart

    auto = get_autostart()
    if args.autostart_status:
        print(f"Start at login: {auto.describe()}")
        return

    try:
        if args.enable_autostart:
            if auto.enable():
                print(f"Autostart enabled: {auto.describe()}.")
            else:
                print("Failed to enable autostart.")
                sys.exit(1)
        else:
            if auto.disable():
                print("Autostart disabled.")
            else:
                print("Failed to disable autostart.")
                sys.exit(1)
    except Exception as exc:
        log.error("autostart command failed: %s", exc)
        print(f"ERROR: {exc}")
        sys.exit(2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dashboard", action="store_true",
                        help="open the dashboard window")
    parser.add_argument("--no-tray", action="store_true",
                        help="run the tracker headless (no tray icon)")
    parser.add_argument("--duration", type=int, default=0,
                        help="headless tracker test run for N seconds")
    parser.add_argument("--autostart-status", action="store_true",
                        help="print the 'start with Windows' setting and exit")
    parser.add_argument("--enable-autostart", action="store_true",
                        help="start automatically at logon, then exit")
    parser.add_argument("--disable-autostart", action="store_true",
                        help="stop starting automatically at logon, then exit")
    parser.add_argument("--autostart-mode", choices=("auto", "task", "run"),
                        default="auto",
                        help="autostart mechanism: 'task' (Task Scheduler, "
                             "needs administrator rights), 'run' (HKCU Run "
                             "key) or 'auto' (task when allowed, else run)")
    args = parser.parse_args()

    if args.autostart_status or args.enable_autostart or args.disable_autostart:
        _run_autostart_command(args)
    elif args.dashboard:
        _run_dashboard()
    else:
        _run_tracker(args)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # windowed exes have no console -- make sure any fatal error
        # lands in the log file instead of vanishing
        log.exception("fatal error - DigitalWellbeing exited")
        sys.exit(1)
