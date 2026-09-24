"""Win32 helpers: foreground window + idle detection (low latency, ctypes)."""

import ctypes
from ctypes import wintypes

_user32 = getattr(ctypes, "windll", None)
if _user32:
    _kernel32 = _user32.kernel32
    _user32 = _user32.user32
else:
    _kernel32 = None

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


def get_idle_seconds() -> float:
    """Seconds since last mouse/keyboard input (native, ~0 latency)."""
    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if not _user32.GetLastInputInfo(ctypes.byref(info)):
        return 0.0
    now_tick = _kernel32.GetTickCount()
    last = info.dwTime
    # handle tick counter wrap (~49 days)
    delta = (now_tick - last) & 0xFFFFFFFF
    return delta / 1000.0


if _user32 and _kernel32:
    _user32.GetForegroundWindow.restype = wintypes.HWND
    _user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND,
                                                 ctypes.POINTER(wintypes.DWORD)]
    _user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    _user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    _user32.GetWindowTextLengthW.restype = ctypes.c_int
    _user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR,
                                       ctypes.c_int]
    _user32.GetWindowTextW.restype = ctypes.c_int
    _user32.GetLastInputInfo.argtypes = [ctypes.POINTER(LASTINPUTINFO)]
    _user32.GetLastInputInfo.restype = wintypes.BOOL
    _kernel32.GetTickCount.restype = wintypes.DWORD


def get_foreground():
    """(pid, exe_name, window_title) of the foreground window, or None."""
    hwnd = _user32.GetForegroundWindow()
    if not hwnd:
        return None
    pid = wintypes.DWORD()
    _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    pid = pid.value or 0

    # window title
    length = _user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    _user32.GetWindowTextW(hwnd, buf, length + 1)
    title = buf.value or ""

    # exe name via psutil (robust, no admin needed for own processes)
    try:
        proc = psutil.Process(pid)
        exe = proc.name() or "unknown.exe"
    except (psutil.Error, OSError):
        exe = "unknown.exe"

    return pid, exe, title
