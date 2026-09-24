"""Linux POSIX file locking using fcntl for single-instance enforcement."""

import fcntl
import os
from pathlib import Path
from src.platform.base import BaseLock
from src.utils.paths import get_data_dir
from src.utils.log import get_logger

log = get_logger("platform.linux.lock")


class LinuxLock(BaseLock):
    def __init__(self, name: str = "tracker.lock"):
        self.lock_dir = get_data_dir()
        self.lock_file = self.lock_dir / name
        self._fd = None

    def acquire(self) -> bool:
        try:
            self.lock_dir.mkdir(parents=True, exist_ok=True)
            self._fd = open(self.lock_file, "w")
            # LOCK_EX: exclusive lock, LOCK_NB: non-blocking
            fcntl.flock(self._fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._fd.write(str(os.getpid()))
            self._fd.flush()
            return True
        except (BlockingIOError, OSError) as e:
            log.info("Another instance is running or failed to lock %s: %s", self.lock_file, e)
            if self._fd:
                try:
                    self._fd.close()
                except Exception:
                    pass
                self._fd = None
            return False

    def release(self) -> None:
        if self._fd:
            try:
                fcntl.flock(self._fd.fileno(), fcntl.LOCK_UN)
                self._fd.close()
            except Exception as e:
                log.warning("Error releasing lock: %s", e)
            self._fd = None
