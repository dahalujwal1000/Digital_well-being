"""Linux power & session watcher using systemd-logind D-Bus signals."""

import subprocess
import threading
from src.platform.base import BasePowerWatcher
from src.utils.log import get_logger

log = get_logger("platform.linux.power")


class LinuxPowerWatcher(BasePowerWatcher):
    def __init__(self, on_sleep=None, on_resume=None, on_shutdown=None,
                 on_lock=None, on_unlock=None):
        super().__init__(on_sleep, on_resume, on_shutdown, on_lock, on_unlock)
        self._thread = None
        self._proc = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True, name="LinuxPowerWatcher")
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._proc:
            try:
                self._proc.terminate()
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def _monitor_loop(self) -> None:
        """Monitor systemd-logind signals using gdbus monitor."""
        cmd = [
            "gdbus", "monitor", "--system",
            "--dest", "org.freedesktop.login1"
        ]
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1
            )
        except Exception as e:
            log.warning("Could not launch gdbus monitor for systemd-logind: %s. Power events disabled.", e)
            return

        log.info("Listening for Linux systemd-logind power & session events via D-Bus")

        try:
            while not self._stop_event.is_set():
                line = self._proc.stdout.readline()
                if not line:
                    break
                line = line.strip()

                # PrepareForSleep(true) -> sleep, PrepareForSleep(false) -> resume
                if "PrepareForSleep" in line:
                    if "(true,)" in line or "(true)" in line or "true" in line:
                        log.info("systemd-logind: PrepareForSleep (true) - suspending")
                        if self.on_sleep:
                            self.on_sleep()
                    elif "(false,)" in line or "(false)" in line or "false" in line:
                        log.info("systemd-logind: PrepareForSleep (false) - resuming")
                        if self.on_resume:
                            self.on_resume()

                # Lock / Unlock signals
                elif "org.freedesktop.login1.Session.Lock" in line:
                    log.info("systemd-logind: Session.Lock")
                    if self.on_lock:
                        self.on_lock()
                elif "org.freedesktop.login1.Session.Unlock" in line:
                    log.info("systemd-logind: Session.Unlock")
                    if self.on_unlock:
                        self.on_unlock()

        except Exception as e:
            if not self._stop_event.is_set():
                log.warning("Exception in Linux power monitor loop: %s", e)
        finally:
            if self._proc:
                try:
                    self._proc.kill()
                except Exception:
                    pass
