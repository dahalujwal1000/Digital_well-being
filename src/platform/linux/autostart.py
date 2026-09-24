"""Linux autostart management using XDG Desktop Entry standard.

Works identically on Fedora, Ubuntu, Debian, Arch, and all freedesktop.org compliant DEs.
Path: ~/.config/autostart/digital-wellbeing.desktop
"""

import os
import sys
from pathlib import Path
from src.platform.base import BaseAutostart
from src.utils.log import get_logger

log = get_logger("platform.linux.autostart")

XDG_AUTOSTART_DIR = Path.home() / ".config" / "autostart"
DESKTOP_ENTRY_FILE = XDG_AUTOSTART_DIR / "digital-wellbeing.desktop"


class LinuxAutostart(BaseAutostart):
    def __init__(self, app_path: Path | None = None):
        self.app_path = app_path or (Path(__file__).resolve().parents[3] / "run_app.py")

    def _get_exec_command(self) -> str:
        # If running as a frozen pyinstaller binary
        if getattr(sys, "frozen", False):
            return f'"{sys.executable}"'
        return f'"{sys.executable}" "{self.app_path}"'

    def is_enabled(self) -> bool:
        try:
            if not DESKTOP_ENTRY_FILE.exists():
                return False
            content = DESKTOP_ENTRY_FILE.read_text(encoding="utf-8")
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("Hidden="):
                    if line.split("=", 1)[1].strip().lower() == "true":
                        return False
                if line.startswith("X-GNOME-Autostart-enabled="):
                    if line.split("=", 1)[1].strip().lower() == "false":
                        return False
            return True
        except Exception as e:
            log.warning("Failed to check Linux autostart: %s", e)
            return False

    def enable(self) -> bool:
        try:
            XDG_AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
            exec_cmd = self._get_exec_command()
            content = (
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Name=Digital Wellbeing\n"
                "Comment=Digital Wellbeing background tracker and system tray icon\n"
                f"Exec={exec_cmd}\n"
                "Terminal=false\n"
                "Hidden=false\n"
                "X-GNOME-Autostart-enabled=true\n"
                "StartupNotify=false\n"
                "Categories=Utility;\n"
            )
            DESKTOP_ENTRY_FILE.write_text(content, encoding="utf-8")
            log.info("Enabled autostart via %s", DESKTOP_ENTRY_FILE)
            return True
        except Exception as e:
            log.warning("Failed to enable Linux autostart: %s", e)
            return False

    def disable(self) -> bool:
        try:
            if DESKTOP_ENTRY_FILE.exists():
                DESKTOP_ENTRY_FILE.unlink()
                log.info("Disabled autostart by removing %s", DESKTOP_ENTRY_FILE)
            return True
        except Exception as e:
            log.warning("Failed to disable Linux autostart: %s", e)
            return False

    def describe(self) -> str:
        if self.is_enabled():
            return "enabled (XDG Autostart ~/.config/autostart)"
        return "disabled"
