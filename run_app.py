"""Digital Wellbeing - single application entry point.

The whole product ships as ONE executable. The same binary starts either
the background tracker (system tray) or the dashboard window:

    DigitalWellbeing.exe                # tracker + system tray (normal use / autostart)
    DigitalWellbeing.exe --dashboard    # open the dashboard window
    DigitalWellbeing.exe --no-tray      # headless tracker, Ctrl+C to stop (testing)
    DigitalWellbeing.exe --duration N   # headless tracker for N seconds (testing)

For development you can run the same thing from source:

    python run_app.py                 # same as the first line above
    python run_app.py --dashboard     # same as --dashboard above
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


def _run_tracker(args: argparse.Namespace) -> None:
    """Start the background tracking engine (optionally with the tray icon)."""
    from src.core.tracker import Tracker
    from src.tray.tray_app import TrayApp

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
        TrayApp(tracker).run()


def _run_dashboard() -> None:
    """Open the dashboard window (blocks until the window closes)."""
    from src.dashboard.app import DigitalWellbeingApp

    app = DigitalWellbeingApp()
    app.mainloop()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dashboard", action="store_true",
                        help="open the dashboard window")
    parser.add_argument("--no-tray", action="store_true",
                        help="run the tracker headless (no tray icon)")
    parser.add_argument("--duration", type=int, default=0,
                        help="headless tracker test run for N seconds")
    args = parser.parse_args()

    if args.dashboard:
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
