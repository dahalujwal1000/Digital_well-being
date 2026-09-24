"""Windows single-instance named mutex lock."""

import sys
from src.platform.base import BaseLock
from src.utils.log import get_logger

log = get_logger("platform.windows.lock")


class WindowsLock(BaseLock):
    def __init__(self, name: str = "Local\\DigitalWellbeing_Tracker_Mutex"):
        self.name = name
        self._handle = None

    def acquire(self) -> bool:
        if sys.platform != "win32":
            return True
        try:
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.windll.kernel32
            kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
            kernel32.CreateMutexW.restype = wintypes.HANDLE
            ERROR_ALREADY_EXISTS = 183

            self._handle = kernel32.CreateMutexW(None, False, self.name)
            if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
                log.info("Another tracker instance is running (mutex exists).")
                return False
            return True
        except Exception as e:
            log.warning("Windows mutex check failed: %s", e)
            return True

    def release(self) -> None:
        if sys.platform != "win32" or not self._handle:
            return
        try:
            import ctypes
            ctypes.windll.kernel32.CloseHandle(self._handle)
        except Exception as e:
            log.warning("Failed to close mutex handle: %s", e)
        self._handle = None
