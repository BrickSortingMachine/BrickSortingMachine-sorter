# MQTT Topic Hierarchy Documentation

## 1. Overview and Design Philosophy

This document outlines the MQTT topic hierarchy for the brick sorting machine project. The design transitions the system from a centralized TCP socket architecture to a decoupled, event-driven model using an MQTT broker.

The core principles of this hierarchy are:

* **Decoupling**: Services no longer need direct knowledge of each other. They communicate through the MQTT broker by publishing messages to specific topics or subscribing to topics of interest.
* **Scalability**: New services can be added to the system with minimal impact on existing components by subscribing to relevant data streams.
* **Clarity and Structure**: The topic hierarchy is designed to be human-readable and logically structured, making it easier to debug, monitor, and extend. The root topic `bricksortingmachine/` provides a clear namespace for the entire application.
* **Single Responsibility**: Each topic has a single, well-defined purpose, such as reporting status, requesting an action, or broadcasting telemetry data.

### General Recommendations

* **QoS (Quality of Service)**:
    * Use **QoS 2** (Exactly once) for commands which cause high computational load (`request`).
    * Use **QoS 1** (At least once) for commands and critical state changes (`result`, `command`) to ensure they are delivered.
    * Use **QoS 0** (At most once) for high-frequency telemetry data (`telemetry`) where losing an occasional message is acceptable.
* **Retained Messages**:
    * Use the **retain flag** (`true`) for `status` topics. This ensures that any new service connecting to the broker immediately receives the last known status of all other services.
    * The retain flag should generally be `false` for all other topics to prevent stale commands or data from being processed.

---

## 2. Topic Hierarchy Breakdown

### Root Topic: `bricksortingmachine/`

All topics related to this application are nested under this root namespace.

---

### 🌳 `bricksortingmachine/vision/`

Topics related to the `vision_service`.

#### `bricksortingmachine/vision/status`

* **Purpose**: To broadcast the online/offline status of the `vision_service`.
* **Published by**: `vision_service`
* **Subscribed by**: `machine_controller`, any monitoring dashboards.
* **Payload**: `online` or `offline` (as a Last Will and Testament message).
* **Retain**: `true`
* **QoS**: 1

#### `bricksortingmachine/vision/telemetry/belt_status`

* **Purpose**: To provide real-time status updates of the conveyor belt as observed by the vision system.
* **Published by**: `vision_service`
* **Subscribed by**: `machine_controller`
* **Payload (JSON)**:
    ```json
    {
      "busy": true,
      "frame": 4512
    }
    ```
* **Retain**: `false`
* **QoS**: 0

---

### 🌳 `bricksortingmachine/classification/`

Topics for the classification workflow.

#### `bricksortingmachine/classification/status`

* **Purpose**: To broadcast the online/offline status of the `classification_service`.
* **Published by**: `classification_service`
* **Subscribed by**: `machine_controller`, `vision_service` (to know if it can send requests).
* **Payload**: `online` or `offline` (LWT).
* **Retain**: `true`
* **QoS**: 1

#### `bricksortingmachine/classification/request`

* **Purpose**: To request the classification of a detected object. This replaces the old `CLF` TCP message.
* **Published by**: `vision_service`
* **Subscribed by**: `classification_service`
* **Payload (JSON)**:
    ```json
    {
      "object_id": "obj_1719875432_abc",
      "image_path": "/path/to/detected/image.jpg"
    }
    ```
* **Retain**: `false`
* **QoS**: 2

#### `bricksortingmachine/classification/result`

* **Purpose**: To publish the result of a classification task. This replaces the old `CLR` TCP message.
* **Published by**: `classification_service`
* **Subscribed by**: `vision_service`, `serial_service`, `machine_controller`.
* **Payload (JSON)**:
    ```json
    {
      "object_id": "obj_1719875432_abc",
      "class": "red_2x4"
    }
    ```
* **Retain**: `false`
* **QoS**: 1

---

### 🌳 `bricksortingmachine/notification/`

Topics related to the `notification_service`.

#### `bricksortingmachine/notification/status`

* **Purpose**: To broadcast the online/offline status of the `notification_service`.
* **Published by**: `notification_service`
* **Subscribed by**: `machine_controller`.
* **Payload**: `online` or `offline` (LWT).
* **Retain**: `true`
* **QoS**: 1

#### `bricksortingmachine/notification/request`

* **Purpose**: To request a notification, such as playing a sound. This replaces the old `NTF` message.
* **Published by**: Any service (e.g., `machine_controller`, `vision_service`).
* **Subscribed by**: `notification_service`
* **Payload (JSON)**:
    ```json
    {
      "type": "sound",
      "message": "error.wav"
    }
    ```
* **Retain**: `false`
* **QoS**: 1

---

### 🌳 `bricksortingmachine/serial/`

Topics related to the `serial_service`.

#### `bricksortingmachine/serial/status`

* **Purpose**: To broadcast the online/offline status of the `serial_service`, which communicates with the hardware.
* **Published by**: `serial_service`
* **Subscribed by**: `machine_controller`
* **Payload**: `online` or `offline` (LWT).
* **Retain**: `true`
* **QoS**: 1

---

### 🌳 `bricksortingmachine/controller/`

Topics for commands and telemetry managed by the central `machine_controller`.

#### `bricksortingmachine/controller/status`

* **Purpose**: To broadcast the online/offline status of the `machine_controller` itself.
* **Published by**: `machine_controller`
* **Subscribed by**: All other services, monitoring dashboards.
* **Payload**: `online` or `offline` (LWT).
* **Retain**: `true`
* **QoS**: 1

#### `bricksortingmachine/controller/command/estop`

* **Purpose**: To issue a soft emergency stop command. This replaces the old `STP` message.
* **Published by**: `vision_service` (or any other service authorized to stop the machine).
* **Subscribed by**: `machine_controller`, `serial_service`.
* **Payload**: `true` or `false`
* **Retain**: `false`
* **QoS**: 1

#### `bricksortingmachine/controller/telemetry/hour_meter`

* **Purpose**: For the controller to periodically publish the machine's hour meter value. This replaces the old `HMV` message.
* **Published by**: `machine_controller`
* **Subscribed by**: `vision_service` (for display on UI), any logging or maintenance service.
* **Payload**: A string or integer representing the hours.
    ```
    5432.7
    ```
* **Retain**: `false`
* **QoS**: 0
