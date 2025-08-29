import curses
import json
import logging
import pathlib
import threading
import time
from typing import List


from sorter.supervisor.log_monitor import LogMonitor
from sorter.supervisor.process_manager import ProcessManager
from sorter.supervisor.service import Service
from sorter.supervisor.tui import TUI


class Supervisor:
    """
    The main class for the supervisor mode. It loads the configuration,
    manages the lifecycle of services, and controls the TUI.
    """

    def __init__(self, config_path: pathlib.Path):
        self.config_path = config_path
        self.services: List[Service] = []
        self.process_manager = ProcessManager()
        self.tui = TUI()
        self.log_monitor = LogMonitor(self)
        self._stop_event = threading.Event()
        self.messages: List[str] = []
        self.message_lock = threading.Lock()
        self._load_config()

    def _load_config(self):
        """Loads the service configuration from the JSON file."""
        logging.info(f"Loading configuration from: {self.config_path}")
        try:
            with open(self.config_path, 'r') as f:
                config_data = json.load(f)
        except FileNotFoundError:
            logging.error(f"Configuration file not found at: {self.config_path}")
            raise
        except json.JSONDecodeError:
            logging.error(f"Invalid JSON in configuration file: {self.config_path}")
            raise

        service_list = config_data.get("services", [])
        if not service_list:
            logging.warning("No services found in the configuration file.")
            return

        for service_data in service_list:
            if not service_data.get("enabled", False):
                logging.info(f"Service '{service_data.get('name')}' is disabled. Skipping.")
                continue

            required_keys = ['name', 'command', 'args']
            if not all(k in service_data for k in required_keys):
                raise ValueError(f"Service config missing required keys in: {service_data}")

            service = Service(
                name=service_data['name'],
                command=service_data['command'],
                enabled=service_data['enabled'],
                args=service_data.get('args', {}),
                restart_attempts=service_data.get('restart_attempts', 0),
                depends_on=service_data.get('depends_on', []),
                startup_delay_seconds=service_data.get('startup_delay_seconds', 0),
            )
            self.services.append(service)
            logging.info(f"Loaded service: {service.name}")

    def get_services(self) -> List[Service]:
        return self.services

    def get_log_dir(self) -> pathlib.Path:
        return self.process_manager.log_dir

    def get_messages(self) -> List[str]:
        with self.message_lock:
            return list(self.messages)

    def add_message(self, message: str, service_name: str):
        with self.message_lock:
            formatted_message = f"[{service_name}] {message}"
            self.messages.append(formatted_message)
            if len(self.messages) > 10:
                self.messages.pop(0)

    def is_shutting_down(self) -> bool:
        return self._stop_event.is_set()

    def shutdown(self):
        if not self.is_shutting_down():
            logging.info("Shutdown initiated by user.")
            self._stop_event.set()

    def restart_all_services(self):
        logging.info("Restarting all services...")
        self.process_manager.stop_all(self.services)
        # The control loop will handle restarting them.
        for service in self.services:
            service.status = "STOPPED"


    def _are_dependencies_met(self, service_to_check: Service) -> bool:
        """Checks if all dependencies for a given service are in the RUNNING state."""
        if not service_to_check.depends_on:
            return True

        for dep_name in service_to_check.depends_on:
            dependency = next((s for s in self.services if s.name == dep_name), None)
            if not dependency or dependency.status != "RUNNING":
                return False
        return True

    def _control_loop(self):
        """The main loop for managing service status, dependencies, and restarts."""
        while not self.is_shutting_down():
            for service in self.services:
                self._update_service_status(service)
            time.sleep(0.5)  # Main loop refresh interval

    def _update_service_status(self, service: Service):
        """Runs a single iteration of the state machine for a given service."""
        process_exit_code = service.process.poll() if service.process else None

        # --- Service State Machine ---
        if service.status in ["STOPPED", "WAITING"]:
            if self._are_dependencies_met(service):
                logging.info(f"Dependencies met for '{service.name}'. Starting...")
                self.process_manager.start_service(service)
                self.log_monitor.start_monitoring(service)
            else:
                service.status = "WAITING"

        elif service.status == "STARTING":
            if process_exit_code is not None:
                logging.error(f"Service '{service.name}' exited immediately with code {process_exit_code}.")
                service.status = "ERROR"
                self.add_message(f"ERROR: Exited immediately (code: {process_exit_code})", service.name)
            elif service.start_time and (time.time() - service.start_time) > service.startup_delay_seconds:
                logging.info(f"Service '{service.name}' successfully started and is now RUNNING.")
                service.status = "RUNNING"

        elif service.status == "RUNNING":
            if process_exit_code is not None:
                logging.error(f"Service '{service.name}' exited unexpectedly with code {process_exit_code}.")
                service.status = "ERROR"
                self.add_message(f"ERROR: Exited unexpectedly (code: {process_exit_code})", service.name)

        elif service.status == "ERROR":
            if service.remaining_restarts > 0 or service.restart_attempts == -1:
                if service.restart_attempts != -1:
                    service.remaining_restarts -= 1

                logging.info(f"Attempting to restart '{service.name}'. Attempts left: {service.remaining_restarts if service.restart_attempts != -1 else 'infinite'}")
                self.add_message(f"WARN: Restarting service. Attempts left: {service.remaining_restarts}", service.name)
                service.status = "RESTARTING"
            else:
                # No more restarts. The service will remain in ERROR state.
                pass

        elif service.status == "RESTARTING":
            # This state provides a brief backoff period before restarting.
            time.sleep(2)
            if self._are_dependencies_met(service):
                logging.info(f"Re-launching service '{service.name}'.")
                self.process_manager.start_service(service)
                self.log_monitor.start_monitoring(service)
            else:
                logging.warning(f"Cannot restart '{service.name}', dependencies are not met. Moving to WAITING.")
                service.status = "WAITING"

    def run(self):
        """Starts the supervisor, including the TUI and control loop."""
        if not self.services:
            logging.warning("No enabled services to run. Exiting.")
            return

        control_thread = threading.Thread(target=self._control_loop)
        control_thread.daemon = True
        control_thread.start()

        try:
            curses.wrapper(self.tui.run, self)
        except curses.error as e:
            logging.error(f"TUI failed with a curses error: {e}")
            print("TUI failed. Your terminal might be too small or not support colors.")
        except Exception as e:
            logging.critical(f"Supervisor crashed: {e}", exc_info=True)
        finally:
            if not self.is_shutting_down():
                self.shutdown()

            logging.info("Waiting for control loop to finish...")
            control_thread.join(timeout=2)

            logging.info("Stopping all services...")
            self.process_manager.stop_all(self.services)
            logging.info("Shutdown complete.")
