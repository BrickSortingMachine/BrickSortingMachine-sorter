# Brick Sorting Machine - MQTT Topic Hierarchy

## Pre-Requisite
- Install [mosquitto mqtt server](https://mosquitto.org/)
- do `not install it as a service` - since unit tests frequently start and stop for clean environment
- Ensure mosquitto installation dir (e.g. `C:\Program Files\mosquitto`) is added to the PATH

This document outlines the proposed MQTT topic hierarchy for the Brick Sorting Machine project. A well-defined topic structure is crucial for maintainable and scalable communication between the distributed services of the machine.

**Root Namespace:** `brick_sorting_machine/`

All topics for the Brick Sorting Machine will be prefixed with `brick_sorting_machine/` to avoid conflicts if other MQTT-enabled systems are present on the same network.

---

## 1. Service Status & Heartbeat

Used by services to announce their presence, current status (e.g., online, offline, error), and send regular heartbeats. MQTT's Last Will and Testament (LWT) feature should be utilized here to automatically update a service's status to "offline" if it disconnects ungracefully.

**Topic Structure:** `brick_sorting_machine/status/<service_name>`

* **`<service_name>`:** Identifier for the service.
    * Examples: `controller`, `vision`, `classification`, `notification`, `serial_interface` (if serial communication is managed as a distinct service publishing to MQTT).
* **Payload (JSON):**
    * On regular publish:
        ```json
        {
          "status": "online", // e.g., "online", "offline", "initializing", "error", "degraded"
          "timestamp": "<iso_timestamp_utc>",
          "version": "<service_version_string>", // e.g., "1.2.0"
          "hostname": "<host_identifier>",
          "message": "<optional_status_message>" // e.g., "Connected to camera X"
        }
        ```
    * LWT Payload:
        ```json
        {
          "status": "offline",
          "timestamp": "<iso_timestamp_utc>"
        }
        ```
* **Publishers:** Each respective service (`controller`, `vision`, etc.).
* **Subscribers:**
    * `controller` (to monitor other services).
    * Monitoring tools or dashboards.
    * Any service that depends on the status of another service.
* **QoS:** Typically 0 or 1 for status updates. LWT should ensure delivery.
* **Retained:** It's often useful to retain the last status message so new subscribers immediately know the current state.

---

## 2. Commands

Used for sending commands or requests from one service to another, typically to trigger an action.

**Topic Structure:** `brick_sorting_machine/command/<target_service_name>/<action>`

* **`<target_service_name>`:** The service intended to receive and act upon the command.
    * Examples: `controller`, `vision`, `classification`, `serial_interface`.
* **`<action>`:** The specific action to be performed.
    * Examples for `controller`: `start_sorting`, `stop_sorting`, `reset_machine`, `calibrate_componentX`.
    * Examples for `vision`: `capture_image`, `start_stream`, `stop_stream`, `set_camera_param`.
    * Examples for `classification`: `classify_image_from_topic`, `load_model`, `get_current_model_info`.
    * Examples for `serial_interface`: `send_raw_command`, `move_servo`, `read_sensor`.
* **Payload (JSON):** Contains parameters necessary for the command. Can be empty if the action itself is sufficient.
    * Example for `brick_sorting_machine/command/controller/start_sorting`:
        ```json
        {
          "batch_id": "batch_20250517_A",
          "sorting_profile": "default_profile"
        }
        ```
    * Example for `brick_sorting_machine/command/vision/set_camera_param`:
        ```json
        {
          "camera_id": "main_conveyor_cam",
          "parameter": "exposure",
          "value": 5000
        }
        ```
    * Example for `brick_sorting_machine/command/classification/load_model`:
        ```json
        {
          "model_path": "models/brick_classifier_v3.h5"
        }
        ```
* **Publishers:**
    * `controller` (orchestrating other services).
    * User Interface (UI) service.
    * Automated scripts or higher-level control systems.
* **Subscribers:** The `<target_service_name>`.
* **QoS:** Typically 1 or 2, as command execution is often critical.

---

## 3. Data & Events

For services to publish their operational data, results, or significant events that occur during operation.

### 3.1. Data Streams

For continuous or frequent data output from services.

**Topic Structure:** `brick_sorting_machine/data/<source_service_name>/<data_type>/[<specific_identifier>]`

* **`<source_service_name>`:** The service generating the data.
    * Examples: `vision`, `classification`, `controller`, `serial_interface`.
* **`<data_type>`:** Describes the kind of data.
    * Examples for `vision`: `image`, `object_detection_raw`, `conveyor_speed_raw`.
    * Examples for `classification`: `classification_result`, `model_performance_metrics`.
    * Examples for `controller`: `motor_status`, `brick_count_per_bin`.
    * Examples for `serial_interface`: `sensor_reading`, `actuator_feedback`.
* **`[<specific_identifier>]` (Optional):** Further refinement, e.g., a camera ID, sensor ID, or a unique ID for a specific data item (like an image).
    * Example: `brick_sorting_machine/data/vision/image/main_conveyor_cam`
    * Example: `brick_sorting_machine/data/vision/image_payload/<image_uuid>` (if image data is large and sent separately)
* **Payload (JSON or Binary):**
    * For structured data (e.g., classification results, sensor readings): JSON.
        ```json
        // brick_sorting_machine/data/classification/classification_result
        {
          "image_id": "<uuid_of_source_image>",
          "timestamp": "<iso_timestamp_utc>",
          "detections": [
            {"class_label": "3001", "confidence": 0.98, "bounding_box": [100, 50, 30, 20]},
            {"class_label": "3022", "confidence": 0.92, "bounding_box": [150, 60, 25, 18]}
          ],
          "processing_time_ms": 85
        }
        ```
    * For binary data (e.g., images): Raw binary. Consider publishing metadata on one topic and the binary payload on another (e.g., `.../image_payload/<uuid>`) if payloads are large.
* **Publishers:** The `<source_service_name>`.
* **Subscribers:**
    * `controller` (for decision making).
    * `notification_service` (to trigger alerts based on data).
    * Data logging services.
    * UI for display.
    * Other services that consume this data (e.g., `classification` might subscribe to `vision`'s image data).
* **QoS:** Depends on criticality. 0 or 1 for frequent data.

### 3.2. Discrete Events

For significant, less frequent occurrences.

**Topic Structure:** `brick_sorting_machine/event/<source_service_name>/<event_category>/[<event_name>]`

* **`<source_service_name>`:** The service where the event originated.
* **`<event_category>`:** Broad classification of the event.
    * Examples: `error`, `warning`, `info`, `milestone`, `system`.
* **`[<event_name>]` (Optional but Recommended):** Specific name of the event.
    * Examples for `controller`: `error/belt_jammed`, `milestone/batch_completed`, `info/bin_full`.
    * Examples for `classification`: `warning/low_confidence_detection`, `info/model_updated`.
* **Payload (JSON):** Provides context about the event.
    ```json
    // brick_sorting_machine/event/controller/error/belt_jammed
    {
      "timestamp": "<iso_timestamp_utc>",
      "location": "main_conveyor_section_3",
      "severity": "critical",
      "details": "Sensor X triggered jam detection."
    }
    ```json
    // brick_sorting_machine/event/controller/milestone/batch_completed
    {
      "timestamp": "<iso_timestamp_utc>",
      "batch_id": "batch_20250517_A",
      "total_sorted": 1250,
      "duration_minutes": 45
    }
    ```
* **Publishers:** The `<source_service_name>`.
* **Subscribers:**
    * `controller`.
    * `notification_service`.
    * UI.
    * Logging and auditing systems.
* **QoS:** Typically 1 or 2 for important events.

---

## 4. Machine & Service State

For publishing the overall state of the machine or detailed state of individual services, beyond simple online/offline status.

**Topic Structure (Overall Machine):** `brick_sorting_machine/state/machine`
**Topic Structure (Specific Service):** `brick_sorting_machine/state/<service_name>`

* **`<service_name>`:** e.g., `controller`, `vision`, `classification`.
* **Payload (JSON):**
    * `brick_sorting_machine/state/machine`:
        ```json
        {
          "timestamp": "<iso_timestamp_utc>",
          "operational_mode": "sorting", // "idle", "sorting", "calibrating", "error_halt"
          "current_batch_id": "batch_20250517_A",
          "bricks_sorted_session": 789,
          "estimated_completion_time": "<iso_timestamp_utc_or_duration>",
          "active_errors": ["belt_jammed_s3"] // list of active error codes/ids
        }
        ```
    * `brick_sorting_machine/state/vision`:
        ```json
        {
          "timestamp": "<iso_timestamp_utc>",
          "camera_status": {
            "main_conveyor_cam": "streaming",
            "entry_cam": "idle"
          },
          "current_fps": 15.5,
          "objects_detected_last_minute": 60
        }
        ```
* **Publishers:**
    * `controller` for `brick_sorting_machine/state/machine`.
    * Respective services for `brick_sorting_machine/state/<service_name>`.
* **Subscribers:** UI, `controller` (for service states), monitoring tools.
* **QoS:** Typically 0 or 1.
* **Retained:** Often useful to retain the last state message.

---

## 5. Configuration

For services to report their current configuration or to be dynamically updated (use with caution for runtime updates).

* **Requesting current config:**
    * Topic: `brick_sorting_machine/config/<service_name>/get`
    * Publisher: `controller`, UI, admin tool.
    * Subscriber: The `<service_name>`.
    * Payload: Empty, or specific keys if only part of the config is needed.
* **Publishing current config:**
    * Topic: `brick_sorting_machine/config/<service_name>/current`
    * Publisher: The `<service_name>` (in response to `/get` or on change/startup).
    * Subscriber: `controller`, UI, logging/auditing.
    * Payload (JSON): The current configuration of the service.
        ```json
        // brick_sorting_machine/config/classification/current
        {
          "active_model": "models/brick_classifier_v3.h5",
          "confidence_threshold": 0.75,
          "image_source_topic": "brick_sorting_machine/data/vision/image/main_conveyor_cam"
        }
        ```
* **Setting/Updating config (Use with caution at runtime):**
    * Topic: `brick_sorting_machine/config/<service_name>/set`
    * Publisher: `controller`, UI, admin tool.
    * Subscriber: The `<service_name>`.
    * Payload (JSON): The configuration parameters to be updated.
* **QoS:** 1 or 2 for reliability.
* **Retained:** `brick_sorting_machine/config/<service_name>/current` could be retained.

---

## 6. Notifications (Aggregated for User)

If the `notification_service` aggregates events and data to create user-facing notifications.

**Topic Structure:** `brick_sorting_machine/notifications/user`

* **Payload (JSON):**
    ```json
    {
      "timestamp": "<iso_timestamp_utc>",
      "level": "info", // "info", "warning", "error", "critical"
      "title": "Bin Full",
      "message": "Bin #3 (Red Bricks) is now full. Please empty.",
      "source_event_ids": ["<uuid_of_bin_full_event>"] // Optional traceability
    }
    ```
* **Publishers:** `notification_service`.
* **Subscribers:** UI, external alerting systems (email, SMS gateway), mobile apps.
* **QoS:** 1 or 2.

---

## 7. Broadcasts

For general messages not fitting specific categories, or for system-wide announcements.

**Topic Structure:** `brick_sorting_machine/broadcast/<message_type>`

* **`<message_type>`:** e.g., `announcement`, `system_update_notice`.
* **Payload (JSON):**
    ```json
    // brick_sorting_machine/broadcast/announcement
    {
      "timestamp": "<iso_timestamp_utc>",
      "sender": "admin_tool",
      "content": "Scheduled maintenance will occur tonight from 2:00 AM to 3:00 AM UTC."
    }
    ```
* **Publishers:** Any service with authority (e.g., `controller`, admin tool).
* **Subscribers:** All or selected services that need to be aware of general broadcasts.
* **QoS:** Typically 0 or 1.

---

## MQTT Wildcards

MQTT wildcards can be used by subscribers to listen to multiple topics:

* **`+` (Single-level wildcard):** Matches any string within a single topic level.
    * `brick_sorting_machine/status/+`: Subscribes to status updates from all services.
    * `brick_sorting_machine/event/controller/+/belt_jammed`: Subscribes to belt jam events from any category under controller events (if the hierarchy was deeper).
    * `brick_sorting_machine/data/vision/+/main_conveyor_cam`: Subscribes to all data types from the main conveyor camera.
* **`#` (Multi-level wildcard):** Matches any number of topic levels from that point downwards. Must be the last character in the topic.
    * `brick_sorting_machine/event/#`: Subscribes to all events from all services.
    * `brick_sorting_machine/data/vision/#`: Subscribes to all data published by the vision service.
    * `brick_sorting_machine/#`: Subscribes to absolutely everything related to the Brick Sorting Machine (use with caution, can be very chatty).

---

This hierarchy aims to be comprehensive yet flexible. It should be reviewed and adapted as the project evolves. Consistent use of JSON for payloads (where applicable) and clear timestamping (UTC) is highly recommended.
