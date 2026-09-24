"""Cross-platform base classes and interfaces for OS-specific functionality."""

from abc import ABC, abstractmethod
from typing import Optional, Tuple


class BaseLock(ABC):
    """Abstract interface for single-instance application locking."""

    @abstractmethod
    def acquire(self) -> bool:
        """Acquire lock. Return True if acquired, False if already held."""
        pass

    @abstractmethod
    def release(self) -> None:
        """Release the lock."""
        pass


class BaseHooks(ABC):
    """Abstract interface for detecting active window and user idle status."""

    @abstractmethod
    def get_idle_seconds(self) -> float:
        """Seconds since last mouse/keyboard input."""
        pass

    @abstractmethod
    def get_foreground(self) -> Optional[Tuple[int, str, str]]:
        """Return (pid, exe_name, window_title) of foreground window, or None."""
        pass


class BasePowerWatcher(ABC):
    """Abstract interface for listening to OS power & session state events."""

    def __init__(self, on_sleep=None, on_resume=None, on_shutdown=None,
                 on_lock=None, on_unlock=None):
        self.on_sleep = on_sleep
        self.on_resume = on_resume
        self.on_shutdown = on_shutdown
        self.on_lock = on_lock
        self.on_unlock = on_unlock

    @abstractmethod
    def start(self) -> None:
        """Start listening for power and session events."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop listening."""
        pass


class BaseAutostart(ABC):
    """Abstract interface for configuring start-at-login."""

    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if autostart is enabled."""
        pass

    @abstractmethod
    def enable(self) -> bool:
        """Enable autostart for the current user."""
        pass

    @abstractmethod
    def disable(self) -> bool:
        """Disable autostart for the current user."""
        pass

    @abstractmethod
    def describe(self) -> str:
        """Return a human-readable status of the autostart setting."""
        pass
