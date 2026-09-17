"""Unit tests for logon autostart (Task Scheduler definition + Run key).

Nothing here touches the machine's real autostart state: the schtasks calls,
the registry writes and the "am I elevated" check are all stubbed.
"""

import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.utils import autostart  # noqa: E402

try:                                # python -m unittest tests.test_autostart
    from . import _quiet          # noqa: F401,E402 - keeps the app log clean
except ImportError:                 # python -m unittest discover -s tests
    import _quiet                 # noqa: F401,E402

NS = "{http://schemas.microsoft.com/windows/2004/02/mit/task}"

try:                              # optional: real Task Scheduler schema check
    import win32com.client
    HAS_COM = True
except Exception:                 # pragma: no cover
    HAS_COM = False


class TaskDefinitionTests(unittest.TestCase):
    """The XML handed to schtasks has to say the right things."""

    def setUp(self):
        self.root = ET.fromstring(autostart.task_xml())

    def _settings(self, name: str) -> str:
        return self.root.findtext(f"{NS}Settings/{NS}{name}")

    def test_namespace_and_uri(self):
        self.assertEqual(self.root.tag, f"{NS}Task")
        self.assertEqual(self.root.findtext(f"{NS}RegistrationInfo/{NS}URI"),
                         f"\\{autostart.TASK_NAME}")

    def test_logon_trigger_for_this_user_with_delay(self):
        trigger = self.root.find(f"{NS}Triggers/{NS}LogonTrigger")
        self.assertIsNotNone(trigger)
        self.assertEqual(trigger.findtext(f"{NS}UserId"),
                         autostart.current_user())
        self.assertEqual(trigger.findtext(f"{NS}Delay"), autostart.LOGON_DELAY)

    def test_never_stops_on_battery(self):
        # a wellbeing tracker that dies when the laptop unplugs is useless
        self.assertEqual(self._settings("DisallowStartIfOnBatteries"), "false")
        self.assertEqual(self._settings("StopIfGoingOnBatteries"), "false")

    def test_no_execution_time_limit(self):
        # PT0S = run forever; the 72h default would kill a long-running tracker
        self.assertEqual(self._settings("ExecutionTimeLimit"), "PT0S")

    def test_second_logon_start_is_ignored(self):
        self.assertEqual(self._settings("MultipleInstancesPolicy"), "IgnoreNew")

    def test_restart_on_failure(self):
        restart = self.root.find(f"{NS}Settings/{NS}RestartOnFailure")
        self.assertIsNotNone(restart)
        self.assertEqual(restart.findtext(f"{NS}Count"),
                         autostart.RESTART_COUNT)
        self.assertEqual(restart.findtext(f"{NS}Interval"),
                         autostart.RESTART_INTERVAL)

    def test_action_matches_the_entry_point(self):
        command, arguments, workdir = autostart.executable_parts()
        action = self.root.find(f"{NS}Actions/{NS}Exec")
        self.assertEqual(action.findtext(f"{NS}Command"), command)
        self.assertEqual(action.findtext(f"{NS}WorkingDirectory"), workdir)
        self.assertEqual(action.findtext(f"{NS}Arguments") or "", arguments)
        self.assertEqual(self.root.find(f"{NS}Actions").get("Context"), "Author")

    def test_principal_runs_without_admin(self):
        principal = self.root.find(f"{NS}Principals/{NS}Principal")
        self.assertEqual(principal.get("id"), "Author")
        self.assertEqual(principal.findtext(f"{NS}RunLevel"), "LeastPrivilege")
        self.assertEqual(principal.findtext(f"{NS}LogonType"),
                         "InteractiveToken")


class CommandLineTests(unittest.TestCase):
    def test_dev_command_points_at_the_entry_point(self):
        line = autostart.command_line()
        self.assertTrue(line.startswith('"'))          # exe path is quoted
        self.assertIn("run_app.py", line)

    def test_frozen_definition_uses_the_exe_directly(self):
        exe = r"C:\Program Files\DigitalWellbeing\DigitalWellbeing.exe"
        with mock.patch.object(sys, "frozen", True, create=True), \
                mock.patch.object(sys, "executable", exe):
            command, arguments, workdir = autostart.executable_parts()
            line = autostart.command_line()
            xml = autostart.task_xml()
        self.assertEqual(command, exe)
        self.assertEqual(arguments, "")
        self.assertEqual(workdir, r"C:\Program Files\DigitalWellbeing")
        self.assertEqual(line, f'"{exe}"')
        self.assertNotIn("<Arguments>", xml)           # nothing to pass

    def test_dev_definition_quotes_the_script(self):
        arguments = ET.fromstring(autostart.task_xml()).findtext(
            f"{NS}Actions/{NS}Exec/{NS}Arguments")
        self.assertTrue(arguments.startswith('"'))
        self.assertTrue(arguments.endswith("run_app.py\""))

    def test_current_user_has_no_xml_metacharacters(self):
        user = autostart.current_user()
        self.assertTrue(user)
        self.assertNotIn("&", user)
        self.assertNotIn("<", user)


class MechanismTests(unittest.TestCase):
    def test_off(self):
        with mock.patch.object(autostart, "task_exists", return_value=False), \
                mock.patch.object(autostart, "run_key_enabled",
                                  return_value=False):
            self.assertIsNone(autostart.mechanism())
            self.assertFalse(autostart.is_enabled())
            self.assertEqual(autostart.describe(), "off")

    def test_task_wins_over_a_leftover_run_key(self):
        with mock.patch.object(autostart, "task_exists", return_value=True), \
                mock.patch.object(autostart, "run_key_enabled",
                                  return_value=True):
            self.assertEqual(autostart.mechanism(), autostart.TASK)

    def test_run_key_only(self):
        with mock.patch.object(autostart, "task_exists", return_value=False), \
                mock.patch.object(autostart, "run_key_enabled",
                                  return_value=True):
            self.assertEqual(autostart.mechanism(), autostart.RUN)
            self.assertTrue(autostart.is_enabled())

    def test_describe_mentions_the_delay_and_the_fallback(self):
        self.assertIn("30s", autostart.describe(autostart.TASK))
        self.assertIn("Run key", autostart.describe(autostart.RUN))
        self.assertTrue(autostart.status_line().startswith("Start with"))


class EnableDisableTests(unittest.TestCase):
    def test_auto_mode_prefers_the_task(self):
        with mock.patch.object(autostart, "_create_task") as create, \
                mock.patch.object(autostart, "_delete_run_key") as drop, \
                mock.patch.object(autostart, "_write_run_key") as write:
            self.assertEqual(autostart.enable(), autostart.TASK)
        create.assert_called_once()
        drop.assert_called_once()               # one mechanism only
        write.assert_not_called()

    def test_auto_mode_falls_back_to_the_run_key(self):
        with mock.patch.object(
                autostart, "_create_task",
                side_effect=autostart.AutostartError("no")), \
                mock.patch.object(autostart, "_write_run_key") as write:
            self.assertEqual(autostart.enable(), autostart.RUN)
        write.assert_called_once()

    def test_auto_mode_tries_the_task_even_without_admin_rights(self):
        # importing a task for the current user works unelevated, so the
        # elevation flag must not short-circuit the attempt
        with mock.patch.object(autostart, "elevated", return_value=False), \
                mock.patch.object(autostart, "_create_task") as create, \
                mock.patch.object(autostart, "_delete_run_key"), \
                mock.patch.object(autostart, "_write_run_key") as write:
            self.assertEqual(autostart.enable(), autostart.TASK)
        create.assert_called_once()
        write.assert_not_called()

    def test_explicit_task_mode_surfaces_the_error(self):
        with mock.patch.object(
                autostart, "_create_task",
                side_effect=autostart.AutostartError("denied")):
            with self.assertRaises(autostart.AutostartError):
                autostart.enable(autostart.TASK)

    def test_explicit_run_mode_skips_the_task(self):
        with mock.patch.object(autostart, "elevated", return_value=True), \
                mock.patch.object(autostart, "_create_task") as create, \
                mock.patch.object(autostart, "_write_run_key") as write:
            self.assertEqual(autostart.enable(autostart.RUN), autostart.RUN)
        create.assert_not_called()
        write.assert_called_once()

    def test_unknown_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            autostart.enable("bogus")

    def test_disable_clears_both_mechanisms(self):
        with mock.patch.object(autostart, "_delete_run_key") as drop, \
                mock.patch.object(autostart, "task_exists", return_value=True), \
                mock.patch.object(autostart, "_delete_task",
                                  return_value=True) as delete:
            autostart.disable()
        drop.assert_called_once()
        delete.assert_called_once()

    def test_disable_reports_an_admin_only_task(self):
        # a task written by the (elevated) installer can only be removed from
        # an admin process: the tray must show this instead of failing silently
        with mock.patch.object(autostart, "_delete_run_key"), \
                mock.patch.object(autostart, "task_exists", return_value=True), \
                mock.patch.object(autostart, "_delete_task",
                                  return_value=False):
            with self.assertRaises(autostart.AutostartError) as ctx:
                autostart.disable()
        self.assertIn("administrator", str(ctx.exception))

    def test_toggle_on(self):
        with mock.patch.object(autostart, "is_enabled", return_value=False), \
                mock.patch.object(autostart, "enable",
                                  return_value=autostart.RUN) as enable:
            self.assertTrue(autostart.toggle())
        enable.assert_called_once()

    def test_toggle_off(self):
        with mock.patch.object(autostart, "is_enabled", return_value=True), \
                mock.patch.object(autostart, "disable") as disable:
            self.assertFalse(autostart.toggle())
        disable.assert_called_once()


class ReconcileTests(unittest.TestCase):
    def test_duplicate_run_key_is_dropped_when_the_task_exists(self):
        with mock.patch.object(autostart, "task_exists", return_value=True), \
                mock.patch.object(autostart, "run_key_enabled",
                                  return_value=True), \
                mock.patch.object(autostart, "_delete_run_key") as drop:
            autostart.reconcile()
        drop.assert_called_once()

    def test_run_key_is_kept_when_no_task_exists(self):
        with mock.patch.object(autostart, "task_exists", return_value=False), \
                mock.patch.object(autostart, "run_key_enabled",
                                  return_value=True), \
                mock.patch.object(autostart, "_delete_run_key") as drop:
            autostart.reconcile()
        drop.assert_not_called()


class SchtasksTests(unittest.TestCase):
    """_create_task() feeds schtasks a UTF-16 XML file."""

    def _capture(self, returncode=0, stderr=""):
        captured = {}

        def fake(arguments):
            arguments = list(arguments)
            path = Path(arguments[arguments.index("/xml") + 1])
            captured["xml_path"] = path
            captured["bytes"] = path.read_bytes()
            captured["arguments"] = arguments
            return mock.Mock(returncode=returncode, stdout="", stderr=stderr)

        return captured, fake

    def test_imports_from_a_utf16_file(self):
        captured, fake = self._capture()
        with mock.patch.object(autostart, "_schtasks", side_effect=fake):
            autostart._create_task()
        self.assertTrue(captured["bytes"].startswith(b"\xff\xfe"))  # BOM
        self.assertIn("/create", captured["arguments"])
        self.assertIn(autostart.TASK_NAME, captured["arguments"])

    def test_temp_file_is_cleaned_up(self):
        captured, fake = self._capture()
        with mock.patch.object(autostart, "_schtasks", side_effect=fake):
            autostart._create_task()
        self.assertFalse(captured["xml_path"].exists())

    def test_access_denied_is_reported_with_advice(self):
        # exactly what a non-elevated process gets back from Windows
        _, fake = self._capture(returncode=1, stderr="ERROR: Access is denied.")
        with mock.patch.object(autostart, "_schtasks", side_effect=fake):
            with self.assertRaises(autostart.AutostartError) as ctx:
                autostart._create_task()
        message = str(ctx.exception)
        self.assertIn("Access is denied", message)
        self.assertIn("administrator", message)

    def test_strict_task_query_surfaces_process_failure(self):
        with mock.patch.object(
                autostart, "_schtasks", side_effect=OSError("unavailable")):
            self.assertFalse(autostart.task_exists())
            with self.assertRaises(autostart.AutostartError):
                autostart.task_exists(strict=True)


@unittest.skipUnless(HAS_COM, "pywin32 is not installed")
class SchemaValidationTests(unittest.TestCase):
    """Let the real Task Scheduler parse the definition.

    Setting XmlText validates against the Windows schema without registering
    (or elevating) anything.
    """

    def _parsed(self, xml: str) -> str:
        service = win32com.client.Dispatch("Schedule.Service")
        service.Connect()
        definition = service.NewTask(0)
        definition.XmlText = xml            # raises on a schema violation
        return definition.XmlText

    def test_windows_accepts_the_dev_definition(self):
        parsed = self._parsed(autostart.task_xml())
        self.assertIn(autostart.LOGON_DELAY, parsed)
        self.assertIn(autostart.TASK_NAME, parsed)

    def test_windows_accepts_the_frozen_definition(self):
        exe = r"C:\Program Files\DigitalWellbeing\DigitalWellbeing.exe"
        with mock.patch.object(sys, "frozen", True, create=True), \
                mock.patch.object(sys, "executable", exe):
            parsed = self._parsed(autostart.task_xml())
        self.assertIn("DigitalWellbeing.exe", parsed)


if __name__ == "__main__":
    unittest.main()
