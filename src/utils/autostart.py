"""Start digital wellbeing automatically at Windows logon.

Two mechanisms exist; only ONE is ever active:

* ``TASK`` - a Windows Task Scheduler "on logon" task (``\\DigitalWellbeing``).
  This is the recommended one: it waits 30s after logon so boot does not
  fight the tracker, it never stops when the laptop goes on battery, it has
  no 72-hour execution limit and Windows restarts it if it ever crashes.
  ``schtasks /create /xml`` imports such a task for the *current* user without
  elevation, which is how the tray toggle can set it up; if a policy or a
  locked-down ACL refuses it (the installer's elevated call always works) the
  Run key below is used instead.
* ``RUN`` - the per-user ``HKCU\\...\\Run`` value. Needs no admin at all, so
  it is the automatic fallback and keeps the tray toggle from dead-ending.

``enable()`` clears the other mechanism and ``reconcile()`` drops a stale
Run key whenever the task exists, so a logon can never start two trackers
(the tracker's own single-instance mutex is the final backstop).
"""

import ctypes
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional
from xml.sax.saxutils import escape

from src.utils.log import get_logger

log = get_logger("autostart")

ROOT = Path(__file__).resolve().parents[2]

TASK = "task"                      # Windows Task Scheduler (usually no admin)
RUN = "run"                        # HKCU\...\Run value (no admin needed)
MODES = ("auto", TASK, RUN)

TASK_NAME = "DigitalWellbeing"
TASK_DESCRIPTION = ("Digital Wellbeing tracker + system tray icon. "
                    "Started automatically when you log in.")
LOGON_DELAY = "PT30S"              # let the desktop settle before starting
RESTART_COUNT = "3"
RESTART_INTERVAL = "PT1M"          # after a crash, retry up to 3x / 1min

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "DigitalWellbeing"

_TASK_XML_NS = "http://schemas.microsoft.com/windows/2004/02/mit/task"
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class AutostartError(RuntimeError):
    """Raised when Windows refused to change the autostart configuration."""


# --------------------------------------------------------------------------
# what gets launched
# --------------------------------------------------------------------------

def _quote(path: str) -> str:
    return f'"{path}"'


def executable_parts() -> tuple:
    """``(command, arguments, working_dir)`` used to start the tracker.

    ``command`` is never quoted (that is what Task Scheduler wants) while
    ``arguments`` is a ready-to-run command-line fragment.
    """
    if getattr(sys, "frozen", False):
        # frozen single exe: the binary itself IS the tracker + tray
        exe = Path(sys.executable)
        return str(exe), "", str(exe.parent)
    # dev / not frozen: use pythonw so no console window flashes at logon
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    exe = pythonw if pythonw.exists() else Path(sys.executable)
    entry = ROOT / "run_app.py"
    return str(exe), _quote(str(entry)), str(ROOT)


def command_line() -> str:
    """Full command line used to start the tracker (Run key value / logs)."""
    command, arguments, _ = executable_parts()
    return f"{_quote(command)} {arguments}".strip()


def current_user() -> str:
    """``MACHINE\\User`` (or ``DOMAIN\\User``) for the current process."""
    domain = os.environ.get("USERDOMAIN", "").strip()
    name = os.environ.get("USERNAME", "").strip()
    if name:
        return f"{domain}\\{name}" if domain else name
    return _username_from_windows()


def _username_from_windows() -> str:
    """Fallback when the environment has no USERNAME (tiny login sessions)."""
    try:
        advapi32 = ctypes.windll.advapi32
        size = ctypes.c_ulong(256)
        buf = ctypes.create_unicode_buffer(size.value)
        if advapi32.GetUserNameW(buf, ctypes.byref(size)):
            return buf.value
    except Exception:                                   # pragma: no cover
        log.exception("could not read the current user name")
    return ""


def task_xml() -> str:
    """The Task Scheduler definition for the on-logon tracker task.

    Written for the Task Scheduler importer: logon trigger for this user only,
    a 30s delay, "ignore new instances", no stop on battery, no execution
    time limit (the tracker is meant to run for days) and a restart policy.
    """
    command, arguments, workdir = executable_parts()
    user = escape(current_user())
    args_xml = (f"      <Arguments>{escape(arguments)}</Arguments>\n"
                if arguments else "")
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="{_TASK_XML_NS}">
  <RegistrationInfo>
    <Description>{escape(TASK_DESCRIPTION)}</Description>
    <URI>\\{TASK_NAME}</URI>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <UserId>{user}</UserId>
      <Delay>{LOGON_DELAY}</Delay>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{user}</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <RestartOnFailure>
      <Count>{RESTART_COUNT}</Count>
      <Interval>{RESTART_INTERVAL}</Interval>
    </RestartOnFailure>
    <StartWhenAvailable>true</StartWhenAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{escape(command)}</Command>
{args_xml}      <WorkingDirectory>{escape(workdir)}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""


# --------------------------------------------------------------------------
# mechanism 1: Task Scheduler
# --------------------------------------------------------------------------

def _schtasks(arguments: list) -> subprocess.CompletedProcess:
    return subprocess.run(["schtasks", *arguments], capture_output=True,
                          text=True, errors="replace", timeout=30,
                          creationflags=_NO_WINDOW)


def task_exists(*, strict: bool = False) -> bool:
    try:
        return _schtasks(["/query", "/tn", TASK_NAME]).returncode == 0
    except Exception as exc:
        log.exception("could not query the startup task")
        if strict:
            raise AutostartError(
                f"could not query the Windows startup task: {exc}") from exc
        return False


def _create_task() -> None:
    """Register the on-logon task.

    Importing a task for the *current* user through ``schtasks /create /xml``
    normally works without elevation (verified on Windows 11, and unlike the
    switch-based ``schtasks /create /sc onlogon`` form), so the tray toggle can
    set this up directly. On a locked-down machine Windows answers "Access is
    denied" and an AutostartError is raised - an elevated caller (the
    installer, or the tray's admin action) always succeeds.

    The definition goes over as an XML file: a file is the only way to express
    the logon delay, the battery rules and the restart policy, and UTF-16 is
    the encoding the Task Scheduler importer expects.
    """
    xml_path = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".xml", encoding="utf-16",
                                         delete=False) as handle:
            xml_path = Path(handle.name)
            handle.write(task_xml())
        result = _schtasks(["/create", "/tn", TASK_NAME, "/xml",
                            str(xml_path), "/f"])
    except Exception as exc:
        raise AutostartError(f"could not run schtasks: {exc}") from exc
    finally:
        if xml_path is not None:
            xml_path.unlink(missing_ok=True)

    if result.returncode != 0:
        raise AutostartError(
            "could not register the Windows startup task "
            f"({_message(result)}). Windows may require administrator rights "
            "for this on your machine - use the installer, or run "
            "'DigitalWellbeing.exe --enable-autostart --autostart-mode task' "
            "as administrator.")
    log.info("registered the on-logon startup task '%s'", TASK_NAME)


def _delete_task() -> bool:
    try:
        result = _schtasks(["/delete", "/tn", TASK_NAME, "/f"])
    except Exception:
        log.exception("could not run schtasks /delete")
        return False
    if result.returncode == 0:
        log.info("removed the startup task '%s'", TASK_NAME)
        return True
    log.warning("schtasks /delete failed: %s", _message(result))
    return False


def _message(result: subprocess.CompletedProcess) -> str:
    text = (result.stderr or result.stdout or "").strip()
    return text.splitlines()[0] if text else f"exit code {result.returncode}"


# --------------------------------------------------------------------------
# mechanism 2: HKCU Run key (no admin needed)
# --------------------------------------------------------------------------

def run_key_enabled() -> bool:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, VALUE_NAME)
            return True
    except FileNotFoundError:
        return False
    except OSError:                                     # pragma: no cover
        log.exception("could not read the Run key")
        return False


def _write_run_key() -> None:
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                        winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, command_line())


def _delete_run_key() -> None:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, VALUE_NAME)
            log.info("removed the Run key autostart value")
    except FileNotFoundError:
        pass                                            # nothing to remove
    except OSError:                                     # pragma: no cover
        log.exception("could not remove the Run key value")


# --------------------------------------------------------------------------
# public API
# --------------------------------------------------------------------------

def elevated() -> bool:
    """True when this process runs with administrator rights.

    Only a hint (tray wording / CLI tip): importing the startup task is
    normally allowed unelevated, and ``enable()`` therefore tries it first.
    """
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:                                   # pragma: no cover
        return False


def mechanism() -> Optional[str]:
    """Which autostart mechanism is installed right now (``None`` = off)."""
    if task_exists():
        return TASK
    if run_key_enabled():
        return RUN
    return None


def is_enabled() -> bool:
    return mechanism() is not None


def describe(mech: Optional[str] = None) -> str:
    """Short human-readable description for the tray menu / CLI."""
    if mech is None:
        mech = mechanism()
    if mech == TASK:
        return "at logon (Windows task, 30s delay)"
    if mech == RUN:
        return "at logon (Run key)"
    return "off"


def status_line() -> str:
    return f"Start with Windows: {describe()}"


def enable(mode: str = "auto") -> str:
    """Install autostart and return the mechanism now in use.

    ``mode``: ``"auto"`` (prefer the scheduled task, fall back to the Run
    key), ``"task"`` (must be the scheduled task, raises otherwise) or
    ``"run"``.

    The task is always attempted first: importing a task for the current user
    works without administrator rights, but if Windows refuses (a policy, a
    locked-down ACL) autostart still gets set up through the Run key rather
    than failing.
    """
    if mode not in MODES:
        raise ValueError(f"unknown autostart mode: {mode!r}")

    if mode != RUN:
        try:
            _create_task()
            _delete_run_key()          # exactly one mechanism, never both
            return TASK
        except AutostartError as exc:
            if mode == TASK:
                raise
            log.warning("could not register the startup task (%s) - falling "
                        "back to the Run key so start at logon still works",
                        exc)
    _write_run_key()
    log.info("autostart enabled via the Run key: %s", command_line())
    return RUN


def disable() -> None:
    """Turn autostart off, whichever mechanism is in use."""
    _delete_run_key()
    if task_exists(strict=True) and not _delete_task():
        raise AutostartError(
            "the Windows startup task can only be removed by an "
            "administrator - run 'DigitalWellbeing.exe --disable-autostart' "
            "as administrator.")


def toggle(mode: str = "auto") -> bool:
    """Flip autostart; returns the new state."""
    if is_enabled():
        disable()
        return False
    return enable(mode) is not None


def reconcile() -> None:
    """Keep exactly one autostart entry.

    Called on every tracker start: when the (stronger) scheduled task exists
    next to an old Run key value, the Run key is dropped so one logon can
    never launch two trackers.
    """
    try:
        if task_exists() and run_key_enabled():
            log.info("startup task found - removing the duplicate Run key")
            _delete_run_key()
    except Exception:
        log.exception("autostart reconcile failed")


def self_elevate(arguments: list) -> bool:
    """Re-run this app elevated (one UAC prompt) with ``arguments``.

    Used by the tray to register/remove the scheduled task, which Windows
    only allows from an administrator process.
    """
    try:
        if getattr(sys, "frozen", False):
            exe = Path(sys.executable)
        else:
            pythonw = Path(sys.executable).with_name("pythonw.exe")
            exe = pythonw if pythonw.exists() else Path(sys.executable)
            arguments = [str(ROOT / "run_app.py"), *arguments]
        params = subprocess.list2cmdline([str(a) for a in arguments])
        result = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", str(exe), params, None, 1)
        if int(result) <= 32:               # 5 / 32 = refused or cancelled
            log.warning("elevation was refused (ShellExecuteW -> %s)", result)
            return False
        return True
    except Exception:
        log.exception("could not request administrator rights")
        return False
