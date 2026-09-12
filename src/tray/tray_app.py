"""System tray icon: Open Dashboard, autostart toggle, today's time, Exit."""

import subprocess
import sys
import threading
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

from src.core.tracker import Tracker
from src.utils import autostart
from src.utils.log import get_logger
from src.utils.time_format import fmt_hm

_ROOT = Path(__file__).resolve().parents[2]
log = get_logger("tray")


def _icon_image() -> Image.Image:
    """Simple blue ring icon drawn in code (no asset files needed)."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([6, 6, 58, 58], outline=(79, 195, 247, 255), width=7)
    d.arc([6, 6, 58, 58], start=90, end=230, fill=(255, 213, 79, 255), width=7)
    return img


def _open_dashboard() -> None:
    try:
        if getattr(sys, "frozen", False):
            # frozen exe: launch the dashboard exe that ships next to us
            exe = Path(sys.executable).parent / "DigitalWellbeingDashboard.exe"
            if not exe.exists():
                log.error("dashboard exe not found at %s", exe)
                return
            subprocess.Popen([str(exe)])
        else:
            subprocess.Popen(
                [sys.executable, str(_ROOT / "run_dashboard.py")],
                cwd=str(_ROOT), creationflags=subprocess.CREATE_NEW_CONSOLE)
    except Exception:
        log.exception("failed to launch dashboard")


class TrayApp:
    def __init__(self, tracker: Tracker):
        self.tracker = tracker
        self._stopped = threading.Event()
        self.icon = pystray.Icon(
            "DigitalWellbeing", _icon_image(), "Digital Wellbeing",
            menu=pystray.Menu(
                pystray.MenuItem("Open Dashboard",
                                 lambda *_: _open_dashboard(),
                                 default=True),
                pystray.MenuItem(lambda item:
                                 fmt_hm(tracker.today_totals()[0])
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
        self._stopped.set()
        self.icon.stop()

    def run(self) -> None:
        threading.Thread(target=self._live_title, daemon=True).start()
        self.icon.run()
        self.tracker.stop()

    def _live_title(self) -> None:
        """Keep the tray tooltip fresh with today's active time."""
        while not self._stopped.is_set():
            try:
                active, _ = self.tracker.today_totals()
                self.icon.title = (f"Digital Wellbeing - "
                                   f"{fmt_hm(active)} active today")
            except Exception:
                log.exception("failed to update tray title")
            self._stopped.wait(30)
