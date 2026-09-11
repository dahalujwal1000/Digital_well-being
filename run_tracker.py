"""Start the background tracker (system tray + Win32 tracking engine).

Usage:
    python run_tracker.py              # tray + tracker (normal use)
    python run_tracker.py --no-tray    # headless, Ctrl+C to stop (testing)
    python run_tracker.py --duration N # headless test run for N seconds
"""

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.tracker import Tracker  # noqa: E402
from src.tray.tray_app import TrayApp  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-tray", action="store_true")
    parser.add_argument("--duration", type=int, default=0)
    args = parser.parse_args()

    tracker = Tracker()
    tracker.start()
    print(f"Tracker running (session {tracker.session_id}). "
          f"DB: {tracker.store.path}")

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


if __name__ == "__main__":
    main()
