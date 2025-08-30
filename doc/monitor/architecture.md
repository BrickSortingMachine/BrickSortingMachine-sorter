# Monitor Mode Architecture

## 1. Overview
The monitor mode is designed as a standalone module within the `sorter` application. It will be implemented in a new `sorter.monitor` package. The architecture is centered around a main `Monitor` class that manages the entire lifecycle of the services.

## 2. Core Components

### 2.1. `Monitor` Class
This is the main class that orchestrates all operations. It will be responsible for:
-   Parsing command-line arguments.
-   Loading and validating the configuration file.
-   Initializing the TUI.
-   Managing the service lifecycle (start, stop, restart).
-   Handling user input from the TUI (e.g., quit, restart all).
-   Ensuring graceful shutdown.

### 2.2. `Service` Class
A data class to represent a single service from the configuration file. It will hold all properties of a service, such as `name`, `command`, `args`, `status`, `pid`, `uptime`, etc.

### 2.3. `ProcessManager`
This component will be responsible for the actual execution and monitoring of child processes. It will use the `subprocess` module to spawn services. For each service, it will:
-   Construct the command-line arguments.
-   Create the process using `subprocess.Popen`.
-   Pass the `SESSION_SECRET` environment variable.
-   Redirect `stdout` and `stderr` to log files.
-   Monitor the process's status.

### 2.4. `TUI`
The Terminal User Interface will be built using Python's standard `curses` library to ensure maximum compatibility. It will run in its own thread to continuously refresh the display without blocking the main process management logic. The TUI will be responsible for:
-   Drawing the layout (header, service table, message panel).
-   Updating the service statuses, PIDs, uptime, etc.
-   Displaying recent "ERROR" and "WARN" messages.
-   Capturing keyboard input for quitting or restarting services.

### 2.5. `LogMonitor`
This component will handle the creation of log directories and files. It will also be responsible for tailing the log files in separate threads to watch for "ERROR" and "WARN" messages in real-time.

## 3. Concurrency Model
The monitor will be heavily multi-threaded to handle multiple tasks concurrently:
-   The **main thread** will handle the initial setup, start the service management loop, and wait for the TUI to exit.
-   A **TUI thread** will be responsible for rendering the user interface at a regular interval.
-   A **keyboard listener thread** will handle user input without blocking the TUI.
-   A **thread for each service's log file** will be spawned to monitor for important messages. This is more scalable than having the main thread do it.

## 4. Key Libraries and Modules
-   **`argparse`**: For parsing CLI arguments.
-   **`json`**: For loading the configuration file.
-   **`subprocess`**: For creating and managing child processes.
-   **`curses`**: For building the TUI.
-   **`threading`**: For concurrent operations.
-   **`os`**, **`datetime`**, **`pathlib`**: For file and directory management.
-   **`secrets`**: For generating the `SESSION_SECRET`.
-   **`time`**: For handling delays and calculating uptime.
