"""Silence the app's own logger while unit tests run.

The app writes %APPDATA%\\DigitalWellbeing\\logs\\wellbeing.log. Several tests
drive code paths that log on purpose:

* ``registered the on-logon startup task 'DigitalWellbeing'`` - test_autostart
  patches ``_schtasks``, so nothing is really registered;
* ``tracker running (session 1)`` / ``tracker stopped (SHUTDOWN), session 1
  closed`` and ``SQLite read error (...) - reconnecting`` - a Tracker driven by
  hand against a temporary database.

Those lines are indistinguishable from real events in the file a user sends in
for support (a plain test run once looked like an autostart change). Importing
this module from a test module detaches the real file handler and leaves a
NullHandler behind, so only production code writes to that log.

Why a separate module instead of ``tests/__init__.py``: the documented command
``python -m unittest discover -s tests`` imports the test modules top-level
(``test_autostart``, ``test_tracker``, ...) and never imports the ``tests``
package, so an ``__init__.py`` would never run.

``src.utils.log`` configures itself lazily, hence the ``_setup()`` call below:
without it, the first ``get_logger()`` inside a later test would attach the
real file handler again.
"""

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils import log as app_log  # noqa: E402


def mute_app_log() -> None:
    """Replace the app logger's handlers with a NullHandler (keeps propagation off)."""
    app_log._setup()                            # attach the real handlers ...
    logger = logging.getLogger("wellbeing")
    for handler in list(logger.handlers):
        handler.close()
    logger.handlers = [logging.NullHandler()]   # ... then throw them away
    logger.propagate = False


mute_app_log()
