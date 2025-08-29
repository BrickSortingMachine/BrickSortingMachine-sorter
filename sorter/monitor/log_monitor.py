import logging
import threading
import time

from sorter.monitor.service import Service


class LogMonitor:
    """
    Manages the real-time monitoring of log files for multiple services,
    each in its own thread.
    """

    def __init__(self, monitor):
        self.monitor = monitor
        self._monitor_threads = {}

    def start_monitoring(self, service: Service):
        """Starts a new daemon thread to monitor the log file for a given service."""
        # Don't start if a monitor for this service is already active.
        if (
            service.name in self._monitor_threads
            and self._monitor_threads[service.name].is_alive()
        ):
            return

        thread = threading.Thread(target=self._tail_log_file, args=(service,))
        thread.daemon = (
            True  # Allows main program to exit even if these threads are running
        )
        self._monitor_threads[service.name] = thread
        thread.start()
        logging.info(f"Started log monitor for '{service.name}'.")

    def _tail_log_file(self, service: Service):
        """
        Tails a log file, watching for new lines containing "ERROR" or "WARN".
        This function is intended to be run in a separate thread.
        """
        # Wait for the log file to be created by the ProcessManager
        while not service.log_file or not service.log_file.exists():
            if self.monitor.is_shutting_down():
                return
            time.sleep(0.2)

        logging.debug(f"Log file for '{service.name}' found. Tailing...")
        try:
            with open(service.log_file, "r") as f:
                # Go to the end of the file in case there's pre-existing text
                f.seek(0, 2)

                # The loop continues as long as the monitor is running and the
                # service is in a state that implies it should be running.
                while not self.monitor.is_shutting_down() and service.status not in [
                    "STOPPED",
                    "ERROR",
                ]:
                    line = f.readline()
                    if not line:
                        time.sleep(0.1)  # No new line, wait a bit
                        continue

                    line = line.strip()
                    if "ERROR" in line:
                        self.monitor.add_message(line, service.name)
                    elif "WARN" in line:
                        self.monitor.add_message(line, service.name)
                        service.has_warned = True  # Set flag for TUI color
        except Exception as e:
            logging.error(
                f"Error while monitoring log for '{service.name}': {e}", exc_info=False
            )

        logging.info(f"Log monitoring for '{service.name}' has finished.")
