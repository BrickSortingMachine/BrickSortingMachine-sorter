# Requirements: Monitor Mode for sorter.py

## 1. Overview
The monitor mode provides a terminal-based dashboard to launch, manage, and monitor the suite of services required for the brick sorting machine. It reads a configuration file to determine which services to run, how to run them, and in what order. It offers real-time status updates, error highlighting, log management, and automatic restarts to simplify the operation of the distributed system.

## 2. Command-Line Interface (CLI)
The monitor shall be launched via the main sorter.py script.
 * Command: `run`
 * Argument:
   * `--config <path>`: (Required) Specifies the path to the JSON configuration file.
 * Example:
   `python sorter.py run --config configs/distributed_setup.json`

## 3. Configuration File (config.json)
The monitor's behavior is defined by a JSON file containing a list of service objects.

### 3.1. Service Object Properties
Each object in the `services` array must define a service to be managed:
 * `name` (string, required): A unique, human-readable name for the service (e.g., "MQTT-Broker", "Vision-Service"). This name is used as an identifier for dependencies and logging.
 * `command` (string, required): The service command to execute (e.g., `controller`, `vision`).
 * `enabled` (boolean, required): If `true`, the monitor will launch this service.
 * `args` (object, required): A key-value map of command-line arguments.
 * `restart_attempts` (integer, optional): The number of times the monitor will attempt to restart the service if it exits unexpectedly. Defaults to `0` (no restarts). A value of `-1` means infinite restarts.
 * `depends_on` (array of strings, optional): A list of service names that must be running before this service is started.
 * `startup_delay_seconds` (integer, optional): The number of seconds to wait after launching this service before proceeding to launch the next one in the sequence. Defaults to `0`.

### 3.2. Example config.json
This example demonstrates a distributed setup with dependencies and restart policies.
```json
{
  "services": [
    {
      "name": "Controller",
      "command": "controller",
      "enabled": true,
      "args": {},
      "restart_attempts": 3
    },
    {
      "name": "Serial-Service",
      "command": "serial",
      "enabled": true,
      "args": {
        "--host": "localhost"
      },
      "restart_attempts": 3,
      "depends_on": ["Controller"],
      "startup_delay_seconds": 2
    },
    {
      "name": "Vision-Service",
      "command": "vision",
      "enabled": true,
      "args": {
        "--host": "192.168.1.10",
        "--collect_class": "sorted"
      },
      "restart_attempts": 1,
      "depends_on": ["Controller"]
    },
    {
      "name": "Classification-Service",
      "command": "classification",
      "enabled": true,
      "args": {
        "--host": "192.168.1.10",
        "--model": "models/model.h5",
        "--enable_mqtt": true
      },
      "restart_attempts": 1,
      "depends_on": ["Controller"]
    },
    {
      "name": "Disabled-Notification-Service",
      "command": "notification",
      "enabled": false,
      "args": {
        "--host": "192.168.1.10",
        "--theme": "robot_german"
      }
    }
  ]
}
```

## 4. Process & Lifecycle Management
 * **Session Management**: On startup, the monitor shall generate a single, cryptographically secure random string to be used as a `SESSION_SECRET`. This secret must be passed as an environment variable to all child processes spawned by the monitor.
 * **Startup Sequence**: The monitor will launch services in the order they appear in the config file, respecting the `depends_on` and `startup_delay_seconds` parameters. A service will not be started until all its dependencies are in a `RUNNING` state.
 * **Automatic Restarts**: If a service with `restart_attempts` > 0 exits with an error, the monitor will attempt to restart it, decrementing the remaining attempt count.
 * **Graceful Shutdown**: Upon receiving an interrupt signal (Ctrl+C), the monitor shall gracefully terminate all child processes it has spawned before exiting itself.

## 5. Logging
 * **Log File Generation**: On each run, the monitor will create a new log directory (e.g., `logs/run_2025-08-29_15-13-00/`). Inside this directory, a separate log file will be created for each enabled service (e.g., `Controller.log`, `Vision-Service.log`).
 * **Output Redirection**: All `stdout` and `stderr` from a service will be redirected to its corresponding log file.
 * **TUI Log Display**: The monitor must scan the output of each service in real-time. Lines containing the case-sensitive strings "ERROR" or "WARN" will be captured and displayed within the TUI.

## 6. Terminal User Interface (TUI)
The monitor shall present a continuously updating TUI for at-a-glance monitoring.

### 6.1. TUI Mockup
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Brick Sorter Monitor                                             ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Service                │ PID    │ Status   │ Uptime  │ Restarts │
├────────────────────────┼────────┼──────────┼─────────┼──────────┤
│ Controller             │ 10451  │ RUNNING  │ 1h 13m  │ 3/3      │
│ Serial-Service         │ 10452  │ WAITING  │ N/A     │ 3/3      │
│ Vision-Service         │ 10454  │ ERROR    │ 5m 14s  │ 0/1      │
│ Classification-Service │ 10453  │ STARTING │ 5s      │ 1/1      │
├────────────────────────┴────────┴──────────┴─────────┴──────────┤
│ [Vision-Service] ERROR: Camera disconnected unexpectedly.        │
│ [Controller]     WARN: Vibration feeder 2 reported high temp.    │
│ [Vision-Service] WARN: Low light levels detected.                │
│ [Serial-Service] WARN: Checksum mismatch on received data.       │
│ [Controller]     ERROR: Main belt motor stalled.                 │
│                                                                  │
│                                                                  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
│ Quit: Q | Restart All: R                                         │
└──────────────────────────────────────────────────────────────────┘
```

### 6.2. TUI Components
 * **Header**: Displays the current log directory path.
 * **Service Status Table**:
   * **Status Column**: Can now display additional states: `WAITING` (waiting for dependencies), `STARTING`, and `RESTARTING`.
   * **Restarts Column**: Shows remaining restart attempts (e.g., `0/1`).
   * **Color Coding**: `RUNNING` (Green), `STOPPED` (Gray), `ERROR` (Red), `WARN` (Yellow), `WAITING`/`STARTING` (Blue). The status of `WARN` is triggered by a "WARN" message in the log but does not stop the process.
 * **Recent Messages Panel**:
   * Displays the most recent captured `ERROR` and `WARN` messages from all services.
   * Each message is prefixed with the name of the service it originated from.
   * Messages are color-coded (Red for `ERROR`, Yellow for `WARN`).
