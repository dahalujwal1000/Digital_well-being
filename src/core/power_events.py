"""Windows session/power events via a hidden message window.

Handles: WM_QUERYENDSESSION / WM_ENDSESSION (shutdown/restart/logoff),
WM_POWERBROADCAST (sleep/resume), WM_WTSSESSION_CHANGE (lock/unlock/logon).
"""

import ctypes
from ctypes import wintypes

_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32
_user32.DefWindowProcW.argtypes = [
    wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
_user32.DefWindowProcW.restype = ctypes.c_longlong

_user32.CreateWindowExW.argtypes = [
    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
_user32.CreateWindowExW.restype = wintypes.HWND

_user32.PostMessageW.argtypes = [
    wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
_user32.PostMessageW.restype = wintypes.BOOL

_user32.GetMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
_user32.GetMessageW.restype = wintypes.BOOL

WM_QUERYENDSESSION = 0x0011
WM_ENDSESSION = 0x0016
WM_POWERBROADCAST = 0x0218
WM_WTSSESSION_CHANGE = 0x02B1
PBT_APMSUSPEND = 0x0004
PBT_APMRESUMESUSPEND = 0x0007
PBT_APMRESUMEAUTOMATIC = 0x0012
WTS_SESSION_LOCK = 0x7
WTS_SESSION_UNLOCK = 0x8
WTS_SESSION_LOGON = 0x5
WTS_SESSION_LOGOFF = 0x6
NOTIFY_FOR_THIS_SESSION = 0

_WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_longlong, wintypes.HWND, wintypes.UINT,
    wintypes.WPARAM, wintypes.LPARAM)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", _WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", ctypes.c_void_p),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


class PowerEventWatcher:
    """Create a hidden window; dispatch session/power events to callbacks.

    callbacks: on_lock(), on_unlock(), on_suspend(), on_resume(),
               on_endsession(reason)  # reason: SHUTDOWN|LOGOFF
    Must run pump() on its own thread until stop() is called.
    """

    def __init__(self, callbacks: dict):
        self.cb = callbacks
        self._proc = _WNDPROC(self._wndproc)   # keep reference (GC!)
        self._hwnd = None
        self._class = None
        self._msg = wintypes.MSG()
        self._running = False

    # ----------------------------------------------------------------- wnd --
    def _wndproc(self, hwnd, msg, wparam, lparam):
        if msg == WM_QUERYENDSESSION:
            return 1
        if msg == WM_ENDSESSION:
            if wparam:
                cb = self.cb.get("on_endsession")
                if cb:
                    cb("SHUTDOWN")
            return 0
        if msg == WM_POWERBROADCAST:
            if wparam == PBT_APMSUSPEND:
                cb = self.cb.get("on_suspend")
                if cb:
                    cb()
            elif wparam in (PBT_APMRESUMEAUTOMATIC, PBT_APMRESUMESUSPEND):
                cb = self.cb.get("on_resume")
                if cb:
                    cb()
            return 1
        if msg == WM_WTSSESSION_CHANGE:
            mapping = {WTS_SESSION_LOCK: "on_lock",
                       WTS_SESSION_UNLOCK: "on_unlock"}
            name = mapping.get(wparam)
            if name and self.cb.get(name):
                self.cb[name]()
            elif wparam == WTS_SESSION_LOGOFF and self.cb.get("on_endsession"):
                self.cb["on_endsession"]("LOGOFF")
        return _user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    # ------------------------------------------------------------- lifecycle --
    def start(self) -> None:
        inst = _kernel32.GetModuleHandleW(None)
        self._class = "DWellbeingEvents"

        wc = WNDCLASSW()
        wc.lpfnWndProc = self._proc
        wc.lpszClassName = self._class
        wc.hInstance = inst
        if not _user32.RegisterClassW(ctypes.byref(wc)):
            raise OSError("RegisterClassW failed")

        self._hwnd = _user32.CreateWindowExW(
            0, self._class, "dwellbeing-events", 0, 0, 0, 0, 0,
            None, None, inst, None)
        if not self._hwnd:
            raise OSError("CreateWindowExW failed")

        # lock/unlock notifications for this session
        wtsapi32 = ctypes.windll.wtsapi32
        wtsapi32.WTSRegisterSessionNotification.argtypes = [
            wintypes.HWND, wintypes.DWORD]
        wtsapi32.WTSRegisterSessionNotification.restype = wintypes.BOOL
        wtsapi32.WTSRegisterSessionNotification(
            self._hwnd, NOTIFY_FOR_THIS_SESSION)
        self._running = True

    def run(self) -> None:
        """Create the hidden window AND pump its messages on ONE thread.

        Win32 message queues belong to the thread that created the window:
        if start() and pump() run on different threads, the pump never sees
        any messages. Call run() from a single dedicated thread.
        """
        self.start()
        self.pump()

    def pump(self) -> None:
        """Blocking message loop; call from a dedicated thread."""
        while self._running and _user32.GetMessageW(
                ctypes.byref(self._msg), None, 0, 0) > 0:
            _user32.TranslateMessage(ctypes.byref(self._msg))
            _user32.DispatchMessageW(ctypes.byref(self._msg))

    def stop(self) -> None:
        self._running = False
        if self._hwnd:
            _user32.PostMessageW(self._hwnd, 0x0010, 0, 0)  # WM_CLOSE
