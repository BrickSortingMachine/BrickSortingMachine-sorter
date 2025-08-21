# Brick Sorting Machine - Usage Guide

This guide provides detailed instructions on how to run each of the core services of the Brick Sorting Machine software.

All services are launched from the main `sorter.py` script, using a command to specify which service to run, followed by any necessary arguments. The general format is:

```bash
python sorter.py <command> [arguments...]
```

The following sections detail the specific command and arguments for each service.

## Controller Service

**Command**: `controller`

The `controller` service is the main brain of the machine. It controls the motors, feeders, and overall machine state. In the legacy TCP model, it also acts as the central communication hub.

### Arguments

-   `--disable_machine`: If set, the service runs in a simulation mode where no hardware (GPIO) calls are made. This is useful for testing the control logic without a physical machine connected.
-   `--disable_belt`: If set, the conveyor belt motor will not be activated.
-   `--disable_vf`: If set, the vibration feeders (vf1/vf2/storage) will not be activated.

### Example

To run the controller service with the physical machine enabled:
```bash
python sorter.py controller
```

To run in simulation mode without any hardware interaction:
```bash
python sorter.py controller --disable_machine
```

## Vision Service

**Command**: `vision`

The `vision` service is the "eyes" of the machine. It uses a camera to watch the conveyor belt, detects bricks, and captures images for classification. It also provides a visual UI for monitoring.

### Arguments

-   `--host <hostname>`:
    **(Required)** The hostname or IP address of the machine where the `controller` service (or MQTT broker) is running.

-   `--collect_class <class_name>`:
    **(Required)** When saving images of detected bricks, this value is used to label the data. This is primarily used when gathering training data. If you are just sorting, you can often set this to `None` or a generic name.

-   `--disable_camera`:
    If set, the service will not try to connect to a physical camera. Instead, it will use sample data from a recording. This is useful for development and testing without the full hardware setup.

-   `--disable_write`:
    If set, the service will not save the captured images of detected bricks to the disk.

-   `--recording <recording_name>`:
    Specifies the name of a recording directory (located in `data/`) to use as the video source when `--disable_camera` is active.

-   `--disable_fullscreen`:
    If set, the visualization window will be displayed as a normal window instead of in fullscreen mode.

### Example

To run the vision service, connecting to a controller on `192.168.1.100` and labeling collected images as `unknown`:
```bash
python sorter.py vision --host 192.168.1.100 --collect_class unknown
```

To run in test mode using a pre-existing recording instead of a live camera:
```bash
python sorter.py vision --host localhost --collect_class test --disable_camera --recording rec_2022-04-21_12-42-30
```

## Classification Service

**Command**: `classification`

The `classification` service is responsible for running the machine learning model to identify bricks from the images captured by the `vision` service. This service is computationally intensive and is often run on a separate, more powerful PC.

### Arguments

-   `--host <hostname>`:
    **(Required)** The hostname or IP address of the machine where the `controller` service (or MQTT broker) is running.

-   `--port <port_number>`:
    The port of the MQTT broker. Defaults to `1883`. This is only used when `--enable_mqtt` is set.

-   `--model <path_to_model>`:
    **(Required)** The file path to the trained CNN model to be loaded (e.g., `models/my_model.h5`).

-   `--disable_cnn`:
    If set, the service will not load the CNN model or perform real predictions. It will return dummy classification results instead. This is useful for testing the communication pipeline without needing a GPU or a long model loading time.

-   `--enable_mqtt`:
    If set, the service will use the MQTT protocol for communication instead of the legacy TCP hub. When this is active, `--host` and `--port` should point to the MQTT broker.

### Example

To run the classification service, connecting to a controller on `192.168.1.100` and using a specific model:
```bash
python sorter.py classification --host 192.168.1.100 --model models/your_model.h5
```

To run using an MQTT broker for communication:
```bash
python sorter.py classification --host <mqtt_broker_ip> --port 1883 --model models/your_model.h5 --enable_mqtt
```

## Serial Service

**Command**: `serial`

The `serial` service is the "hands" of the machine. It listens for classification results and translates them into commands sent over a serial (USB) connection to the microcontroller (e.g., an Arduino) that controls the physical sorting mechanism.

### Arguments

-   `--host <hostname>`:
    **(Required)** The hostname or IP address of the machine where the `controller` service (or MQTT broker) is running.

-   `--disable_network`:
    If set, the service will not attempt to connect to the network. This is useful for testing the serial hardware connection in isolation.

### Example

To run the serial service and connect to a controller on `192.168.1.100`:
```bash
python sorter.py serial --host 192.168.1.100
```

## Notification Service

**Command**: `notification`

The `notification` service is the "voice" of the machine. It provides auditory feedback by playing sounds for different events (e.g., a sound for each classified brick) and can send push notifications for critical alerts.

### Arguments

-   `--host <hostname>`:
    **(Required)** The hostname or IP address of the machine where the `controller` service (or MQTT broker) is running.

-   `--disable_network`:
    If set, the service will not attempt to connect to the network.

-   `--theme <theme_name>`:
    **(Required)** The name of the sound theme to use. The theme corresponds to a subdirectory in the `sounds/` directory (e.g., `robot_german`).

### Example

To run the notification service using the `robot_german` sound theme:
```bash
python sorter.py notification --host 192.168.1.100 --theme robot_german
```

## Practical Examples

The following examples show how to launch the services together in common configurations.

### Scenario 1: All Services on a Single Machine

This setup is common for development and testing. All services run on the same machine and communicate via `localhost`. This example uses the legacy TCP hub model.

**Terminal 1: Controller**
```bash
python sorter.py controller
```

**Terminal 2: Vision Service**
```bash
python sorter.py vision --host localhost --collect_class test
```

**Terminal 3: Classification Service**
```bash
python sorter.py classification --host localhost --model models/your_model.h5
```

**Terminal 4: Serial Service**
```bash
python sorter.py serial --host localhost
```

**Terminal 5: Notification Service**
```bash
python sorter.py notification --host localhost --theme robot_german
```

### Scenario 2: Distributed Setup (Raspberry Pi + PC)

This is a typical production setup. The `controller` and `serial` services run on a Raspberry Pi connected to the hardware, while the more intensive `vision` and `classification` services run on a separate, more powerful PC. This example assumes an MQTT broker is running on the Raspberry Pi.

Let's assume the Raspberry Pi has the IP address `192.168.1.10`.

**On the Raspberry Pi (`192.168.1.10`):**

**Terminal 1: Controller**
```bash
# The controller runs locally to manage the hardware (motors, etc.).
python sorter.py controller
```

**Terminal 2: Serial Service**
```bash
# Connects to the local MQTT broker to receive classification results.
python sorter.py serial --host localhost
```

**On the powerful PC:**

**Terminal 1: Vision Service**
```bash
# Connects to the MQTT broker on the Pi to send classification requests.
python sorter.py vision --host 192.168.1.10 --collect_class sorted
```

**Terminal 2: Classification Service**
```bash
# Connects to the MQTT broker on the Pi. Must use --enable_mqtt.
python sorter.py classification --host 192.168.1.10 --model models/your_model.h5 --enable_mqtt
```

**Terminal 3: Notification Service (Optional)**
```bash
# Can run on the PC, Pi, or another machine. Connects to the broker on the Pi.
python sorter.py notification --host 192.168.1.10 --theme robot_german
```
