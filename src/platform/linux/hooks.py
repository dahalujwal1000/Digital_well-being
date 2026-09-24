"""Linux window & idle hooks with support for X11, GNOME/Wayland, and generic fallbacks."""

import os
import subprocess
import sys
import time
from typing import Optional, Tuple
import psutil

from src.platform.base import BaseHooks
from src.utils.log import get_logger

log = get_logger("platform.linux.hooks")


class LinuxHooks(BaseHooks):
    def __init__(self):
        self._session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
        self._x11_available = bool(os.environ.get("DISPLAY"))
        self._has_xprintidle = None
        self._has_xdotool = None
        self._logged_idle_fallback = False
        self._logged_active_fallback = False

    def _check_command(self, cmd: str) -> bool:
        try:
            res = subprocess.run(["which", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return res.returncode == 0
        except Exception:
            return False

    def get_idle_seconds(self) -> float:
        """Get idle seconds from xprintidle, XScreenSaver, or D-Bus Mutter/ScreenSaver."""
        # 1. Try xprintidle if on X11 / Xwayland
        if self._has_xprintidle is None:
            self._has_xprintidle = self._check_command("xprintidle")

        if self._has_xprintidle:
            try:
                res = subprocess.run(["xprintidle"], capture_output=True, text=True, timeout=1)
                if res.returncode == 0 and res.stdout.strip().isdigit():
                    return int(res.stdout.strip()) / 1000.0
            except Exception as e:
                log.debug("xprintidle failed: %s", e)

        # 2. Try X11 libXss via ctypes
        if self._x11_available:
            try:
                import ctypes
                x11 = ctypes.cdll.LoadLibrary("libX11.so.6")
                xss = ctypes.cdll.LoadLibrary("libXss.so.1")

                class XScreenSaverInfo(ctypes.Structure):
                    _fields_ = [
                        ("window", ctypes.c_ulong),
                        ("state", ctypes.c_int),
                        ("kind", ctypes.c_int),
                        ("til_or_since", ctypes.c_ulong),
                        ("idle", ctypes.c_ulong),
                        ("eventMask", ctypes.c_ulong)
                    ]

                display = x11.XOpenDisplay(None)
                if display:
                    try:
                        xss.XScreenSaverAllocInfo.restype = ctypes.POINTER(XScreenSaverInfo)
                        info = xss.XScreenSaverAllocInfo()
                        root = x11.XDefaultRootWindow(display)
                        if xss.XScreenSaverQueryInfo(display, root, info):
                            idle_ms = info.contents.idle
                            x11.XFree(info)
                            return idle_ms / 1000.0
                    finally:
                        x11.XCloseDisplay(display)
            except Exception as e:
                log.debug("libXss idle check failed: %s", e)

        # 3. Wayland / GNOME Mutter D-Bus IdleMonitor
        try:
            res = subprocess.run([
                "gdbus", "call", "--session",
                "--dest", "org.gnome.Mutter.IdleMonitor",
                "--object-path", "/org/gnome/Mutter/IdleMonitor/Core",
                "--method", "org.gnome.Mutter.IdleMonitor.GetIdletime"
            ], capture_output=True, text=True, timeout=1)
            if res.returncode == 0:
                # Output format: (uint64 12345,)
                out = res.stdout.strip()
                if "uint64" in out:
                    val = out.split("uint64")[1].replace(")", "").replace(",", "").strip()
                    if val.isdigit():
                        return int(val) / 1000.0
        except Exception as e:
            log.debug("GNOME Mutter IdleMonitor D-Bus query failed: %s", e)

        if not self._logged_idle_fallback:
            log.info("No supported native idle monitor found; defaulting idle time to 0.0")
            self._logged_idle_fallback = True

        return 0.0

    def get_foreground(self) -> Optional[Tuple[int, str, str]]:
        """Return (pid, exe_name, window_title) of active window."""
        # 1. Try xdotool if installed
        if self._has_xdotool is None:
            self._has_xdotool = self._check_command("xdotool")

        if self._has_xdotool:
            try:
                res_win = subprocess.run(["xdotool", "getactivewindow"], capture_output=True, text=True, timeout=1)
                if res_win.returncode == 0 and res_win.stdout.strip().isdigit():
                    wid = res_win.stdout.strip()
                    # window title
                    res_title = subprocess.run(["xdotool", "getwindowname", wid], capture_output=True, text=True, timeout=1)
                    title = res_title.stdout.strip() if res_title.returncode == 0 else ""
                    # pid
                    res_pid = subprocess.run(["xdotool", "getwindowpid", wid], capture_output=True, text=True, timeout=1)
                    pid = int(res_pid.stdout.strip()) if res_pid.returncode == 0 and res_pid.stdout.strip().isdigit() else 0
                    
                    exe = ""
                    if pid > 0:
                        try:
                            proc = psutil.Process(pid)
                            exe = proc.name()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    return (pid, exe, title)
            except Exception as e:
                log.debug("xdotool check failed: %s", e)

        # 2. Try X11 root window _NET_ACTIVE_WINDOW via xprop or python-xlib
        if self._check_command("xprop"):
            try:
                res = subprocess.run(["xprop", "-root", "_NET_ACTIVE_WINDOW"], capture_output=True, text=True, timeout=1)
                if res.returncode == 0 and "window id #" in res.stdout:
                    wid = res.stdout.split("window id #")[-1].strip().split()[0]
                    if wid and wid != "0x0":
                        # query title and WM_CLASS
                        res_props = subprocess.run(["xprop", "-id", wid, "WM_NAME", "WM_CLASS", "_NET_WM_PID"],
                                                   capture_output=True, text=True, timeout=1)
                        title = ""
                        exe = ""
                        pid = 0
                        for line in res_props.stdout.splitlines():
                            if line.startswith("WM_NAME(") or line.startswith("_NET_WM_NAME("):
                                parts = line.split("=", 1)
                                if len(parts) > 1:
                                    title = parts[1].strip().strip('"')
                            elif line.startswith("WM_CLASS("):
                                parts = line.split("=", 1)
                                if len(parts) > 1:
                                    classes = [c.strip().strip('"') for c in parts[1].split(",")]
                                    if classes:
                                        exe = classes[-1]
                            elif line.startswith("_NET_WM_PID("):
                                parts = line.split("=", 1)
                                if len(parts) > 1 and parts[1].strip().isdigit():
                                    pid = int(parts[1].strip())
                        if pid > 0 and not exe:
                            try:
                                exe = psutil.Process(pid).name()
                            except Exception:
                                pass
                        return (pid, exe, title)
            except Exception as e:
                log.debug("xprop check failed: %s", e)

        # 3. GNOME Shell / Wayland via gdbus eval or gnome-shell extension
        # If running in GNOME on Wayland, fall back gracefully
        if not self._logged_active_fallback:
            log.info("No active window inspector found on this session; active window will be unknown.")
            self._logged_active_fallback = True

        return None
