"""Cross-platform base paths conforming to Windows and Linux XDG conventions."""

import os
import sys
from pathlib import Path


def get_data_dir() -> Path:
    """Return the application data directory where database and state are stored."""
    if sys.platform == "win32":
        app_data = os.environ.get("APPDATA")
        if app_data:
            base = Path(app_data)
        else:
            base = Path.home() / "AppData" / "Roaming"
        return base / "DigitalWellbeing"
    else:
        # XDG Base Directory specification for Linux/Unix
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            base = Path(xdg_data_home)
        else:
            base = Path.home() / ".local" / "share"
        return base / "digital-wellbeing"


def get_log_dir() -> Path:
    """Return the application log directory."""
    if sys.platform == "win32":
        return get_data_dir() / "logs"
    else:
        xdg_state_home = os.environ.get("XDG_STATE_HOME")
        if xdg_state_home:
            base = Path(xdg_state_home)
        else:
            base = Path.home() / ".local" / "state"
        return base / "digital-wellbeing" / "logs"
