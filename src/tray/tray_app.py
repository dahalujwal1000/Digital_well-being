"""System tray icon: Open Dashboard, autostart toggle, today's time, Exit."""

import subprocess
import sys
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

from src.core.tracker import Tracker
from src.utils import autostart
from src.utils.time_format import fmt_hm

_ROOT = Path(__file__).resolve().parents[2]


def _icon_image() -> Image.Image:
    """Simple blue ring icon drawn in code (no asset files needed)."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([6, 6, 58, 58], outline=(79, 195, 247, 255), width=7)
    d.arc([6, 6, 58, 58], start=90, end=230, fill=(255, 213, 79, 255), width=7)
    return img


def _open_dashboard() -> None:
    subprocess.Popen(
        [sys.executable, str(_ROOT / "run_dashboard.py")],
        cwd=str(_ROOT), creationflags=subprocess.CREATE_NEW_CONSOLE)


class TrayApp:
    def __init__(self, tracker: Tracker):
        self.tracker = tracker
        self.icon = pystray.Icon(
            "DigitalWellbeing", _icon_image(), "Digital Wellbeing",
            menu=pystray.Menu(
                pystray.MenuItem("Open Dashboard",
                                 lambda *_: _open_dashboard(),
                                 default=True),
                pystray.MenuItem(lambda item: fmt_hm(*tracker.today_totals())
                                 + " active today",
                                 lambda *_: None, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Start with Windows",
                                 self._toggle_autostart,
                                 checked=lambda item: autostart.is_enabled()),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Exit", self._exit)))

    @staticmethod
    def _toggle_autostart(*_) -> None:
        autostart.toggle()

    def _exit(self, *_):
        self.icon.stop()

    def run(self) -> None:
        self.icon.run()
        self.tracker.stop()
