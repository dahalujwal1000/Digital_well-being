"""Autostart via HKCU Run key (no admin needed)."""

import sys
from pathlib import Path

import winreg

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "DigitalWellbeing"


def _open() -> winreg.HKEYType:
    return winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                          winreg.KEY_SET_VALUE)


def command() -> str:
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    exe = pythonw if pythonw.exists() else Path(sys.executable)
    entry = Path(__file__).resolve().parents[2] / "run_tracker.py"
    return f'"{exe}" "{entry}"'


def is_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, VALUE_NAME)
            return True
    except FileNotFoundError:
        return False


def enable() -> None:
    with _open() as key:
        winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, command())


def disable() -> None:
    try:
        with _open() as key:
            winreg.DeleteValue(key, VALUE_NAME)
    except FileNotFoundError:
        pass


def toggle() -> bool:
    if is_enabled():
        disable()
        return False
    enable()
    return True
