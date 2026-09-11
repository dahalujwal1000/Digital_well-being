"""Digital Wellbeing for Windows - Dashboard entry point."""

import sys
from pathlib import Path

# Allow running as: python run_dashboard.py  OR  python -m src.dashboard.app
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dashboard.app import DigitalWellbeingApp


def main() -> None:
    app = DigitalWellbeingApp()
    app.mainloop()


if __name__ == "__main__":
    main()
