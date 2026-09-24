"""System tray icon: Open Dashboard, today's time, startup settings, Exit."""

import subprocess
import sys
import threading
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

from src.core.tracker import Tracker
from src.platform import get_autostart
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
            # frozen: relaunch the SAME single exe in dashboard mode
            subprocess.Popen([sys.executable, "--dashboard"])
        else:
            # dev: run the unified entry point in dashboard mode (no new
            # console -- the dashboard is a GUI, a console window just flashes)
            subprocess.Popen(
                [sys.executable, str(_ROOT / "run_app.py"), "--dashboard"],
                cwd=str(_ROOT))
    except Exception:
        log.exception("failed to launch dashboard")


class TrayApp:
    def __init__(self, tracker: Tracker):
        self.tracker = tracker
        self._stopped = threading.Event()
        self.auto = get_autostart()

        menu_items = [
            pystray.MenuItem("Open Dashboard",
                             lambda *_: _open_dashboard(),
                             default=True),
            pystray.MenuItem(lambda item:
                             fmt_hm(tracker.today_totals()[0])
                             + " active today",
                             lambda *_: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Start at Login",
                             self._toggle_autostart,
                             checked=lambda item: self.auto.is_enabled()),
            pystray.MenuItem(lambda item:
                             f"Startup: {self.auto.describe()}",
                             lambda *_: None, enabled=False),
        ]

        if sys.platform == "win32":
            from src.utils import autostart
            menu_items.append(
                pystray.MenuItem("Use startup task (admin)...",
                                 self._use_startup_task,
                                 enabled=lambda item:
                                 autostart.mechanism() != autostart.TASK)
            )

        menu_items.extend([
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self._exit)
        ])

        self.icon = pystray.Icon(
            "DigitalWellbeing", _icon_image(), "Digital Wellbeing",
            menu=pystray.Menu(*menu_items))

    def _toggle_autostart(self, *_):
        """Flip start-at-logon."""
        try:
            enabled = self.auto.toggle()
        except Exception as exc:
            log.warning("autostart toggle failed: %s", exc)
            self._notify(str(exc), "Start at Login")
            return
        if enabled:
            self._notify(f"Digital Wellbeing now starts "
                         f"{self.auto.describe()}.", "Start at Login")
        else:
            self._notify("Digital Wellbeing no longer starts at logon.",
                         "Start at Login")

    def _use_startup_task(self, *_):
        """Register the recommended on-logon task (one UAC prompt) on Windows."""
        if sys.platform != "win32":
            return
        from src.utils import autostart
        if autostart.mechanism() == autostart.TASK:
            return
        if not autostart.self_elevate(
                ["--enable-autostart", "--autostart-mode", "task"]):
            self._notify("Administrator rights are needed to register the "
                         "Windows startup task.", "Start at Login")

    def _notify(self, message: str, title: str) -> None:
        """Tray balloon - a failure here must never break the menu."""
        try:
            self.icon.notify(message, title)
        except Exception:
            log.exception("tray notification failed")

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
