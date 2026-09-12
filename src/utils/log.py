"""App-wide logging: rotating file in %APPDATA%\\DigitalWellbeing\\logs.

get_logger(name) returns a logger that writes to file AND console.
Errors are never silent again -- every except block that swallows an
exception should log at warning level.
"""

import logging
import logging.handlers
from pathlib import Path

APP_DIR = Path.home() / "AppData" / "Roaming" / "DigitalWellbeing"
LOG_DIR = APP_DIR / "logs"
LOG_FILE = LOG_DIR / "wellbeing.log"

_configured = False


def _setup() -> None:
    global _configured
    if _configured:
        return
    _configured = True
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            LOG_FILE, maxBytes=1_000_000, backupCount=2, encoding="utf-8")
    except OSError:                      # e.g. no writable profile dir
        handler = logging.NullHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"))
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(
        "%(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger("wellbeing")
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    root.addHandler(console)
    root.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Namespaced logger under 'wellbeing', e.g. get_logger('tracker')."""
    _setup()
    return logging.getLogger(f"wellbeing.{name}")
