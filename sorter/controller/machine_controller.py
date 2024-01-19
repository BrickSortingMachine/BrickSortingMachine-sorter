import datetime
import enum
import logging
import threading
import time

import sorter.controller.gpio_controller
import sorter.controller.machine_state
import sorter.network.tcp_server


class VibrationFeederState(enum.Enum):
    STOPPED = 0
    RUNNING = 1
    PAUSED = 1


class StorageState(enum.Enum):
    STOPPED = 0
    RUNNING = 1


class MachineController:
    def __init__(self, enable_device, enable_belt, disable_server, enable_vf):
        # back-ref for command handler to this
        MachineControllerCommandHandler.machine_controller = self

        # hardware
        self.gpio = sorter.controller.gpio_controller.GPIOController(enable_device)

        # state machine
        self.state = sorter.controller.machine_state.MachineState()

        # skip network server (for testing)
        self.disable_server = disable_server

        # disable belt/vf
        self.enable_belt = enable_belt
        self.enable_vf = enable_vf

        # network
        if not self.disable_server:
            self.tcp_server = sorter.network.tcp_server.TcpServer(
                "0.0.0.0", 5005, MachineControllerCommandHandler
            )
            self.tcp_server.start()
            time.sleep(1)

        # thread
        self.control_thread_cycles_per_second = 25
        self.adapted_cps = self.control_thread_cycles_per_second

        self.last_state_output = None
        self.last_belt_percentage = 0

    def start_control_thread(self):
        self.control_thread_stop_requested = False
        self.control_thread = threading.Thread(target=self.thread_fct)
        self.control_thread.daemon = True  # have no explicit stopping mechanism
        self.control_thread.start()
        self.control_thread.name = "Machine Controller"

    def stop_control_thread(self):
        self.tcp_server.stop()

        logging.info("Storage thread: Stop requested")
        self.control_thread_stop_requested = True
        self.control_thread.join()

    def event_classification_result(self, predicted_class):
        pass

    def event_scanner_belt_status_received(self, belt_busy, frame_index):
        if belt_busy:
            self.state.input_event_belt_busy(datetime.datetime.now())
        else:
            self.state.input_event_belt_nonBusy(datetime.datetime.now())

    def event_client_hello(self, name):
        logging.warning("Client hello - Name: %s" % name)
        if name == "VisionService":
            self.state.input_event_vision_service_connected(datetime.datetime.now())

    def event_client_disconnected(self, name):
        logging.warning("Client disconnected - Name: %s" % name)
        if name == "VisionService":
            self.state.input_event_vision_service_disconnected(datetime.datetime.now())

    def event_soft_estop(self, stopped):
        self.state.input_event_soft_estop(stopped, datetime.datetime.now())

    def thread_fct(self):
        logging.info("MachineController: Thread running")
        last_dt = datetime.datetime.now()
        cycle_index = 0
        cps_smoothed = None
        while not self.control_thread_stop_requested:
            self.thread_step(cycle_index)

            dt = datetime.datetime.now()
            d_sec = (dt - last_dt).total_seconds()
            cps = 1.0 / d_sec if d_sec > 0.0 else 0.0
            cps_smoothed = (
                0.9 * cps_smoothed + 0.1 * cps if cps_smoothed is not None else cps
            )
            if cycle_index % 100 == 99:
                delta_cps = self.control_thread_cycles_per_second - cps_smoothed
                self.adapted_cps += 0.25 * delta_cps
            if cycle_index % 300 == 299:
                pass  # logging.info('CPS - Actual: %.2f Target: %.2f Adapted: %.2f' % (cps_smoothed, self.control_thread_cycles_per_second, self.adapted_cps))
            last_dt = dt
            cycle_index += 1

            time.sleep(1.0 / self.adapted_cps)
        logging.info("MachineController: Thread stopped.")

    def thread_step(self, cycle_index):
        output = self.state.cycle(datetime.datetime.now())
        self.last_state_output = output

        # speed percentage
        vf1_percentage = 100 if output.vf1_active else 0
        vf2_percentage = 100 if output.vf2_active else 0
        # 30 for small parts, 50 for larger ones
        storage_percentage = 25 if output.storage_active else 0
        if output.belt_active:
            # speed up slowly
            belt_precentage = min(100, self.last_belt_percentage + 10)
        else:
            belt_precentage = 0
        self.last_belt_percentage = belt_precentage

        if not self.enable_belt:
            belt_precentage = 0
        if not self.enable_vf:
            vf1_percentage = 0
            vf2_percentage = 0
            storage_percentage = 0

        # gpio
        self.gpio.set_speed_vf1(vf1_percentage)
        self.gpio.set_speed_vf2(vf2_percentage)
        self.gpio.set_speed_storage(storage_percentage)
        self.gpio.set_speed_belt(belt_precentage)

        # cyclic sending hour meter
        self.send_hour_meter(cycle_index)

    def send_hour_meter(self, cycle_index):
        if cycle_index % 500 == 0:
            # hour meter value
            v = self.state.get_hour_meter_value()

            # tcp connection to vision
            handler = self.tcp_server.get_handler_by_name("VisionService")
            if handler is not None:
                handler.sendall(b"HMV %f" % v)


class MachineControllerCommandHandler(sorter.network.tcp_server.RequestHandler):
    def __init__(self, request, client_address, server) -> None:
        super().__init__(request, client_address, server)

    def process_custom_command(self, message):
        command = message[:3]

        # BST - Belt Status
        if command == b"BST":
            # b'BST busy 57'
            logging.info('Received command BST: "%s"' % message)
            part_list = str(message, "utf-8").split(" ")
            belt_busy = part_list[1] == "busy"
            belt_busy_frame_index = int(part_list[2])
            self.machine_controller.event_scanner_belt_status_received(
                belt_busy, belt_busy_frame_index
            )

        # STP - Stop
        elif command == b"STP":
            # b'STP true'
            logging.info('Received command STP: "%s"' % message)
            part_list = str(message, "utf-8").split(" ")
            stopped = part_list[1] == "true"
            self.machine_controller.event_soft_estop(stopped)

        # CLF - Classification Request (fwd to classification service)
        elif command == b"CLF":
            # b'CLF image_34053485.png'
            logging.info('Received command CLF: "%s"' % message)
            cs = self.tcp_server.get_handler_by_name("ClassificationService")
            if cs is None:
                logging.warning(
                    "Received CLF request but ClassificationService not connected"
                )

            else:
                # fwd message
                cs.sendall(message)

        # CLR - Classification Result (fwd to vision service)
        elif command == b"CLR":
            # b'CLF image_34053485.png'
            logging.info('Received command CLR: "%s"' % message)

            # sorter servo
            part_list = str(message, "utf-8").split(" ")
            self.machine_controller.event_classification_result(
                predicted_class=part_list[2]
            )

            # fwd to vision
            ns = self.tcp_server.get_handler_by_name("VisionService")
            if ns is None:
                logging.warning("Received CLF request but VisionService not connected")

            else:
                # fwd message
                ns.sendall(message)

            # fwd to serial
            ss = self.tcp_server.get_handler_by_name("SerialService")
            if ss is not None:
                ss.sendall(message)

        # NTF - Notification (fwd to notification service)
        elif command == b"NTF":
            # b'NTF image_34053485.png'
            logging.info('Received command NTF: "%s"' % message)
            ns = self.tcp_server.get_handler_by_name("NotificationService")
            if ns is None:
                logging.warning("Received NTF but NotificationService not connected")

            else:
                # fwd message
                ns.sendall(message)

        else:
            raise Exception("Received unsupported command: " "%s" "" % command)

    def event_client_hello(self):
        self.machine_controller.event_client_hello(self.name)

    def event_client_disconnected(self):
        self.machine_controller.event_client_disconnected(self.name)
