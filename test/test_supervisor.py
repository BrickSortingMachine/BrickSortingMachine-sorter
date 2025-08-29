import json
import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch, mock_open

from sorter.supervisor.supervisor import Supervisor
from sorter.supervisor.service import Service
from sorter.supervisor.process_manager import ProcessManager

class TestSupervisor(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory for configs if it doesn't exist
        self.config_dir = pathlib.Path("test_configs_temp")
        self.config_dir.mkdir(exist_ok=True)
        self.config_path = self.config_dir / "test_config.json"

    def tearDown(self):
        # Clean up the temporary config file and directory
        if self.config_path.exists():
            self.config_path.unlink()
        # Only remove the directory if it's empty
        if self.config_dir.exists() and not any(self.config_dir.iterdir()):
            self.config_dir.rmdir()

    def _write_config(self, data):
        with open(self.config_path, 'w') as f:
            json.dump(data, f)

    def test_load_valid_config(self):
        """Tests that a valid configuration is loaded and parsed correctly."""
        config_data = {
            "services": [
                {
                    "name": "TestService1",
                    "command": "test1",
                    "enabled": True,
                    "args": {"--foo": "bar"},
                    "restart_attempts": 3,
                    "depends_on": ["dep1"],
                    "startup_delay_seconds": 2
                },
                {
                    "name": "DisabledService",
                    "command": "test2",
                    "enabled": False,
                    "args": {}
                }
            ]
        }
        self._write_config(config_data)

        # Patch the ProcessManager to avoid creating log directories
        with patch('sorter.supervisor.process_manager.ProcessManager._create_log_directory'):
            supervisor = Supervisor(self.config_path)

        self.assertEqual(len(supervisor.services), 1)
        service = supervisor.services[0]
        self.assertEqual(service.name, "TestService1")
        self.assertEqual(service.command, "test1")
        self.assertEqual(service.args, {"--foo": "bar"})
        self.assertEqual(service.restart_attempts, 3)
        self.assertEqual(service.depends_on, ["dep1"])
        self.assertEqual(service.startup_delay_seconds, 2)

    def test_load_config_missing_required_key(self):
        """Tests that loading a config with a missing required key raises a ValueError."""
        config_data = {
            "services": [{"name": "Incomplete", "enabled": True, "args": {}}]
        }
        self._write_config(config_data)
        with patch('sorter.supervisor.process_manager.ProcessManager._create_log_directory'):
            with self.assertRaises(ValueError):
                Supervisor(self.config_path)

    def test_load_invalid_json(self):
        """Tests that loading a malformed JSON file raises a JSONDecodeError."""
        with open(self.config_path, 'w') as f:
            f.write("{'services': [}") # Invalid JSON
        with patch('sorter.supervisor.process_manager.ProcessManager._create_log_directory'):
            with self.assertRaises(json.JSONDecodeError):
                Supervisor(self.config_path)

    @patch('sorter.supervisor.process_manager.subprocess.Popen')
    def test_process_manager_command_construction(self, mock_popen):
        """Tests that the ProcessManager constructs service commands correctly."""
        # We don't need a real supervisor for this, just the ProcessManager
        pm = ProcessManager()

        service = Service(
            name="CmdTest", command="my-command", enabled=True,
            args={"--host": "localhost", "--port": "8080", "--verbose": True, "--disabled-feature": False},
            restart_attempts=0, depends_on=[], startup_delay_seconds=0
        )

        # Mock the open call to avoid creating real log files
        with patch('builtins.open', mock_open()):
            pm.start_service(service)

        mock_popen.assert_called_once()
        call_args, call_kwargs = mock_popen.call_args

        # Check the command list
        command_list = call_args[0]
        self.assertEqual(command_list[0], sys.executable)
        self.assertEqual(command_list[1], "sorter.py")
        self.assertEqual(command_list[2], "my-command")
        self.assertIn("--host", command_list)
        self.assertIn("localhost", command_list)
        self.assertIn("--port", command_list)
        self.assertIn("8080", command_list)
        self.assertIn("--verbose", command_list)
        # The boolean `False` argument should not be present in the final command
        self.assertNotIn("--disabled-feature", command_list)

        # Check the environment variables
        env = call_kwargs.get('env')
        self.assertIn("SESSION_SECRET", env)
        self.assertEqual(env["PYTHONUNBUFFERED"], "1")


class TestSupervisorLogic(unittest.TestCase):

    def setUp(self):
        # We need a supervisor instance, but we'll mock its dependencies
        # Patch ProcessManager and LogMonitor to avoid side effects
        self.process_manager_patch = patch('sorter.supervisor.supervisor.ProcessManager')
        self.log_monitor_patch = patch('sorter.supervisor.supervisor.LogMonitor')
        self.MockProcessManager = self.process_manager_patch.start()
        self.MockLogMonitor = self.log_monitor_patch.start()

        # We also need a dummy config path
        self.config_path = pathlib.Path("dummy_config.json")
        with patch('builtins.open', mock_open(read_data='{"services": []}')):
            self.supervisor = Supervisor(self.config_path)

        # Mock the manager and monitor instances on the supervisor
        self.supervisor.process_manager = self.MockProcessManager()
        self.supervisor.log_monitor = self.MockLogMonitor()

    def tearDown(self):
        self.process_manager_patch.stop()
        self.log_monitor_patch.stop()

    def test_service_waits_for_dependency(self):
        """A service should go to WAITING if its dependency is not RUNNING."""
        dep_service = Service(name="Dep1", command="c1", enabled=True, args={}, restart_attempts=0, depends_on=[], startup_delay_seconds=0)
        dep_service.status = "STARTING" # Not running yet

        main_service = Service(name="Main", command="c2", enabled=True, args={}, restart_attempts=0, depends_on=["Dep1"], startup_delay_seconds=0)
        main_service.status = "STOPPED"

        self.supervisor.services = [dep_service, main_service]

        self.supervisor._update_service_status(main_service)

        self.assertEqual(main_service.status, "WAITING")
        self.supervisor.process_manager.start_service.assert_not_called()

    def test_service_starts_when_dependency_is_running(self):
        """A service should start if its dependency is RUNNING."""
        dep_service = Service(name="Dep1", command="c1", enabled=True, args={}, restart_attempts=0, depends_on=[], startup_delay_seconds=0)
        dep_service.status = "RUNNING"

        main_service = Service(name="Main", command="c2", enabled=True, args={}, restart_attempts=0, depends_on=["Dep1"], startup_delay_seconds=0)
        main_service.status = "WAITING"

        self.supervisor.services = [dep_service, main_service]

        self.supervisor._update_service_status(main_service)

        self.supervisor.process_manager.start_service.assert_called_with(main_service)

    def test_running_service_fails_and_goes_to_error(self):
        """A RUNNING service whose process has exited should go to ERROR state."""
        service = Service(name="S1", command="c1", enabled=True, args={}, restart_attempts=1, depends_on=[], startup_delay_seconds=0)
        service.status = "RUNNING"
        # Mock the process to have exited with an error code
        service.process = MagicMock()
        service.process.poll.return_value = 1 # Non-zero exit code

        self.supervisor.services = [service]
        self.supervisor._update_service_status(service)

        self.assertEqual(service.status, "ERROR")

    @patch('sorter.supervisor.supervisor.time.sleep', return_value=None)
    def test_error_service_restarts(self, mock_sleep):
        """An ERROR service with remaining restarts should go to RESTARTING."""
        service = Service(name="S1", command="c1", enabled=True, args={}, restart_attempts=3, depends_on=[], startup_delay_seconds=0)
        service.remaining_restarts = 2
        service.status = "ERROR"

        self.supervisor.services = [service]
        self.supervisor._update_service_status(service)

        self.assertEqual(service.status, "RESTARTING")
        self.assertEqual(service.remaining_restarts, 1) # Should be decremented

    def test_error_service_with_no_restarts_stays_error(self):
        """An ERROR service with no restarts left should remain in ERROR state."""
        service = Service(name="S1", command="c1", enabled=True, args={}, restart_attempts=1, depends_on=[], startup_delay_seconds=0)
        service.remaining_restarts = 0 # No attempts left
        service.status = "ERROR"

        self.supervisor.services = [service]
        self.supervisor._update_service_status(service)

        self.assertEqual(service.status, "ERROR")
        # Ensure we didn't try to start it again
        self.supervisor.process_manager.start_service.assert_not_called()


if __name__ == '__main__':
    unittest.main()
