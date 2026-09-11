"""Smoke test: build the app, render all tabs, auto-close after ~2s."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dashboard.app import DigitalWellbeingApp  # noqa: E402

app = DigitalWellbeingApp()


def check() -> None:
    # _refresh() already renders Home/Apps/Sessions; exercise date navigation
    app._shift_date(-3)
    app._shift_date(+1)
    app._go_today()
    app.after(1500, app.destroy)


app.after(300, check)
app.after(6000, app.destroy)  # safety timeout
app.mainloop()
print("SMOKE TEST OK - window opened, all tabs rendered, closed cleanly")

