# Serial Service Documentation

## Introduction

The `serial_service` is responsible for all communication with the physical hardware controllers via serial connections. Its primary role is to abstract the low-level details of serial communication.

The service is automatically detecting and connecting to new serial devices as they become available. It uses a handler-based architecture, allowing for different types of hardware controllers to be integrated by implementing a specific connection handler.

## Documentation

### `SerialService`

This is the main class and entry point for the service. It initializes the `SerialConnectionManager` and registers the necessary handlers for the hardware controllers. Currently, it registers the `SlideSerialConnectionHandler` to manage the slide controller.

The service also includes a TCP client (`SSTcpClient`) to receive classification results from other parts of the system. When a classification result is received, it is forwarded to the appropriate handler to trigger a physical action.

**Usage Example:**
```python
# Create the serial service
serial_service = SerialService(host='localhost', disable_network=False)

# The service automatically starts the connection manager and registers handlers.
# For example, the slide controller handler is registered like this:
self.slide = SlideSerialConnectionHandler()
self.manager.register_handler("slide-controller", self.slide)
```

### `SerialConnectionManager`

The `SerialConnectionManager` is the heart of the serial communication system. Its key responsibilities include:

*   **Device Discovery**: It automatically scans for available serial devices. To improve reliability, it looks for devices in `/dev/serial/by-path/` and `/dev/serial/by-id/`, which provide stable and persistent device identifiers.
*   **Connection Management**: It handles the lifecycle of serial connections, including connecting to new devices and cleaning up when a device is disconnected.
*   **Device Identification**: Once a connection is established, it sends a `HLO` message to identify the device. The device is expected to respond with `HLO <device_id>`, allowing the manager to associate the correct handler with the connection.
*   **Handler Registration**: Other services can register handlers for specific device IDs. When a device with a matching ID is connected, the manager forwards all communication to and from that device to the registered handler.

**Internal Workings:**
Device discovery and identification:
```python
def get_device_list(self):
    """
    Gets a list of all serial devices that are not on the exclude list.
    """
    potential_symlinks = glob.glob("/dev/serial/by-path/*") + glob.glob(
        "/dev/serial/by-id/*"
    )
    # ... filtering logic ...
    return list(allowed_devices)

def identify_connection(self, connection):
    connection.write(b"HLO\n")
    time.sleep(0.5)
    data = connection.readline().decode("UTF-8").strip()
    if data.startswith("HLO "):
        identifier = data.split(" ")[1]
        return identifier
```

#### Configuration

The `SerialConnectionManager` can be configured to ignore specific serial devices. This is useful for preventing the sorter from connecting to other USB-to-serial devices that might be attached to the system. The configuration is done in `config.json`:

```json
{
    "serial_exclude_by_path": [
        "pci-0000:00:14.0-usb-0:3.4.4:1.0-port0"
    ],
    "serial_exclude_by_id": [
        "usb-Arduino__www.arduino.cc__Arduino_Mega_2560_7583231313835160C170-if00"
    ]
}
```

*   `serial_exclude_by_path`: A list of device paths (from `/dev/serial/by-path`) to exclude.
*   `serial_exclude_by_id`: A list of device IDs (from `/dev/serial/by-id`) to exclude.

### `SerialConnectionHandler`

This is an abstract base class that defines the interface for all serial connection handlers. It provides a set of event-based methods that are called by the `SerialConnectionManager`:

*   `event_connected(connection)`: Called when a new connection is established.
*   `event_disconnected(connection)`: Called when a connection is lost.
*   `event_data_received(connection, data)`: Called when data is received from the serial device.

**Handler Structure:**
```python
class MyCustomHandler(SerialConnectionHandlerBase):
    def event_connected(self, connection):
        print("Device connected!")

    def event_disconnected(self, connection):
        print("Device disconnected!")

    def event_data_received(self, connection, data: bytes):
        print(f"Received data: {data}")
```

### `SlideSerialConnectionHandler`

This is the concrete implementation of a `SerialConnectionHandler` for the slide controller. It is responsible for the following:

*   **Receiving Classification Results**: It receives the predicted class for a sorted part.
*   **Position Mapping**: It uses a `class_pose_map` dictionary to map the predicted class to a specific rotation and elevation (`rot`, `el`) of the slide.
*   **Controlling the Slide**: It sends commands to the slide controller via the serial connection to move the slide to the correct position. The command format is `GOT <elevation> <rotation>\n`.
*   **Auto-Return to Center**: It uses an asynchronous timeout (`TimeoutAsync`) to automatically return the slide to its central (skip) position after a few seconds of inactivity.

**Position Mapping and Control:**
```python
class_pose_map = {
    "skip": {"rot": 90, "el": 100},
    "brick1x": {"rot": 58, "el": 100},
    # ... other classes
}

def move_slide(self, rot: int, el: int):
    msg = bytes(f"GOT {el} {rot}\n", "utf-8")
    self.get_connection().write(msg)
```
