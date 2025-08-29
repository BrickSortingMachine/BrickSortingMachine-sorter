import datetime
import logging
import os
import pathlib
import secrets
import subprocess
import sys
import time

from sorter.supervisor.service import Service


class ProcessManager:
    """Handles the creation, monitoring, and termination of service processes."""

    def __init__(self):
        self.session_secret = secrets.token_hex(16)
        self.log_dir = self._create_log_directory()
        self._log_file_handles = {}

    def _create_log_directory(self) -> pathlib.Path:
        """Creates a timestamped directory for the current supervisor run."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_dir = pathlib.Path(f"logs/run_{timestamp}")
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            logging.info(f"Log directory created at: {log_dir}")
            return log_dir
        except OSError as e:
            logging.error(f"Failed to create log directory {log_dir}: {e}")
            raise

    def start_service(self, service: Service):
        """Constructs the command and starts a service in a new process."""
        # Do not start if it's already running
        if service.process and service.process.poll() is None:
            logging.warning(f"Service '{service.name}' is already running.")
            return

        command = [sys.executable, "sorter.py", service.command]
        for arg, value in service.args.items():
            command.append(arg)
            # Some args might not have values (e.g., --enable_mqtt)
            if value is not None and not isinstance(value, bool):
                command.append(str(value))
            elif isinstance(value, bool) and value is False:
                # if a bool arg is false, we don't add it
                command.pop()


        env = os.environ.copy()
        env["SESSION_SECRET"] = self.session_secret
        # Ensure real-time output from child processes
        env["PYTHONUNBUFFERED"] = "1"

        log_file_path = self.log_dir / f"{service.name}.log"
        service.log_file = log_file_path
        log_file_handle = open(log_file_path, 'w')
        self._log_file_handles[service.name] = log_file_handle

        logging.info(f"Starting service '{service.name}': {' '.join(command)}")
        try:
            process = subprocess.Popen(
                command,
                stdout=log_file_handle,
                stderr=subprocess.STDOUT,
                env=env,
                text=True,
                bufsize=1,  # Line-buffered
            )
            service.process = process
            service.pid = process.pid
            service.start_time = time.time()
            service.status = "STARTING"
        except FileNotFoundError:
            logging.error(f"Command not found for service '{service.name}'. Is 'sorter.py' in the right path?")
            service.status = "ERROR"
        except Exception as e:
            logging.error(f"Failed to start service '{service.name}': {e}")
            service.status = "ERROR"

    def stop_service(self, service: Service):
        """Stops a running service process."""
        if not service.process or service.process.poll() is not None:
            return  # Process is not running

        logging.info(f"Stopping service '{service.name}' (PID: {service.pid})")
        try:
            service.process.terminate()
            service.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logging.warning(f"Service '{service.name}' did not terminate gracefully. Sending SIGKILL.")
            service.process.kill()
        except Exception as e:
            logging.error(f"Error while stopping service '{service.name}': {e}")

        service.status = "STOPPED"
        service.pid = None
        service.process = None

        if service.name in self._log_file_handles:
            self._log_file_handles[service.name].close()
            del self._log_file_handles[service.name]

    def stop_all(self, services: list[Service]):
        """Stops all services managed by the supervisor."""
        logging.info("Stopping all services...")
        for service in reversed(services):
            self.stop_service(service)

        # Ensure all log files are closed
        for handle in self._log_file_handles.values():
            handle.close()
        self._log_file_handles.clear()
        logging.info("All services have been stopped.")
