# Monitor Mode Implementation Plan

## Phase 1: Project Scaffolding and Setup (1-2 hours)
1.  **Create `sorter/monitor` package:**
    -   Create a new directory `sorter/monitor`.
    -   Add an `__init__.py` file to make it a package.
2.  **Add `run` command to `sorter.py`:**
    -   Modify `sorter.py` to add a new subparser for the `run` command.
    -   The subparser should accept a `--config` argument.
    -   Create a `run_monitor` function that will be called when the `run` command is used.
3.  **Create main `Monitor` class:**
    -   Create `sorter/monitor/monitor.py`.
    -   Define the `Monitor` class with an `__init__` method that takes the config path.

## Phase 2: Configuration and Service Handling (2-3 hours)
1.  **Implement `Service` data class:**
    -   Create `sorter/monitor/service.py`.
    -   Define a `Service` class (e.g., using `@dataclass`) to store service properties.
2.  **Implement configuration loading:**
    -   In the `Monitor` class, add a method to load the JSON config file.
    -   Parse the `services` array into a list of `Service` objects.
    -   Perform basic validation (e.g., check for required fields).
3.  **Create a sample `config.json`:**
    -   Create `configs/distributed_setup.json` based on the example in the requirements for testing purposes.

## Phase 3: Process Management (3-4 hours)
1.  **Implement `ProcessManager`:**
    -   Create `sorter/monitor/process_manager.py`.
    -   Implement a `start_service` method that takes a `Service` object and uses `subprocess.Popen` to launch it.
    -   The command should be constructed as `python sorter.py <command> [args]`.
    -   Generate and pass the `SESSION_SECRET` as an environment variable.
2.  **Implement log redirection:**
    -   Create the log directory `logs/run_<timestamp>`.
    -   Redirect `stdout` and `stderr` of the child process to a service-specific log file within the log directory.
3.  **Implement `stop_service` method:**
    -   Add a method to terminate a running process gracefully (`.terminate()`) and forcefully if necessary (`.kill()`).

## Phase 4: TUI Development (4-6 hours)
1.  **Set up `curses` wrapper:**
    -   Create `sorter/monitor/tui.py`.
    -   Create a `TUI` class that initializes and cleans up the `curses` screen.
2.  **Implement TUI layout:**
    -   Add methods to draw the header, the service table, and the message panel.
3.  **Implement TUI update loop:**
    -   The `TUI` class should have an `update` method that takes the list of services and recent messages.
    -   This method will redraw the screen with the latest data.
    -   Run the TUI in a separate thread.
4.  **Implement color coding:**
    -   Add logic to display text in different colors based on service status or message type.

## Phase 5: Core Monitor Logic (3-5 hours)
1.  **Implement main loop in `Monitor`:**
    -   This loop will periodically check the status of all managed services.
2.  **Implement startup sequence:**
    -   Add logic to start services in order, respecting `depends_on` and `startup_delay_seconds`.
    -   Update the service status to `WAITING`, `STARTING`, `RUNNING`.
3.  **Implement automatic restarts:**
    -   If a process has exited with a non-zero code, check its `restart_attempts`.
    -   If there are remaining attempts, restart the service.
4.  **Implement graceful shutdown:**
    -   Catch `KeyboardInterrupt` (`Ctrl+C`).
    -   Call the `stop_service` method for all running services before exiting.

## Phase 6: Logging and Monitoring (2-3 hours)
1.  **Implement log monitoring:**
    -   Create a `LogMonitor` class in `sorter/monitor/log_monitor.py`.
    -   For each service, spawn a thread that tails its log file.
    -   When "ERROR" or "WARN" is detected, add the message to a shared queue.
2.  **Integrate with TUI:**
    -   The `Monitor` will read from the message queue and pass the messages to the `TUI` for display.

## Phase 7: Testing and Finalization (3-4 hours)
1.  **Write unit tests:**
    -   Create `test/test_monitor.py`.
    -   Write tests for configuration loading and validation.
    -   Write tests for the process command generation.
    -   Mock `subprocess` and test the service lifecycle logic (start, stop, restart).
2.  **Manual testing:**
    -   Run the monitor with the sample config file.
    -   Verify that all services start and stop correctly.
    -   Kill a service manually to test the restart functionality.
    -   Check the log files for correct output.
    -   Verify the TUI displays all information correctly.
3.  **Code review and refactoring:**
    -   Review the code for clarity, consistency, and adherence to best practices.
    -   Add comments and docstrings where necessary.
