"""Platform adapter factory providing OS-specific hooks, power watcher, autostart, and locking."""

import sys
from typing import Tuple, Optional

from src.platform.base import BaseHooks, BasePowerWatcher, BaseAutostart, BaseLock


def get_lock() -> BaseLock:
    if sys.platform == "win32":
        from src.platform.windows.lock import WindowsLock
        return WindowsLock()
    else:
        from src.platform.linux.lock import LinuxLock
        return LinuxLock()


def get_hooks() -> BaseHooks:
    if sys.platform == "win32":
        class WindowsHooks(BaseHooks):
            def get_idle_seconds(self) -> float:
                from src.core.win32_hooks import get_idle_seconds
                return get_idle_seconds()

            def get_foreground(self) -> Optional[Tuple[int, str, str]]:
                from src.core.win32_hooks import get_foreground
                return get_foreground()
        return WindowsHooks()
    else:
        from src.platform.linux.hooks import LinuxHooks
        return LinuxHooks()


def get_power_watcher(callbacks: dict):
    if sys.platform == "win32":
        from src.core.power_events import PowerEventWatcher
        return PowerEventWatcher(callbacks)
    else:
        from src.platform.linux.power import LinuxPowerWatcher
        watcher = LinuxPowerWatcher(
            on_sleep=callbacks.get("on_suspend"),
            on_resume=callbacks.get("on_resume"),
            on_shutdown=lambda: callbacks.get("on_endsession")("SHUTDOWN") if callbacks.get("on_endsession") else None,
            on_lock=callbacks.get("on_lock"),
            on_unlock=callbacks.get("on_unlock")
        )
        # Match PowerEventWatcher interface: provide .run() and .stop()
        watcher.run = watcher.start
        return watcher


def get_autostart() -> BaseAutostart:
    if sys.platform == "win32":
        from src.utils import autostart
        class WindowsAutostart(BaseAutostart):
            def is_enabled(self) -> bool:
                return autostart.is_enabled()
            def enable(self) -> bool:
                try:
                    autostart.enable("auto")
                    return True
                except Exception:
                    return False
            def disable(self) -> bool:
                try:
                    autostart.disable()
                    return True
                except Exception:
                    return False
            def describe(self) -> str:
                return autostart.describe()
        return WindowsAutostart()
    else:
        from src.platform.linux.autostart import LinuxAutostart
        return LinuxAutostart()
