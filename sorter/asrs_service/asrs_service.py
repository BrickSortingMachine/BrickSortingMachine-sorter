import logging
import threading
import time
import random

from grbl_streamer import GrblStreamer

import sorter.network.tcp_client
import sorter.classification_service.classification_service

event_grbl_rx_buffer_percent_zero = threading.Event()

wait_event_str = None
wait_data_0 = None
wait_event = threading.Event()


def wait_prepare(event_str, data_0=None):
    global wait_event_str
    global wait_data_0
    wait_event.clear()
    wait_event_str = event_str
    wait_data_0 = data_0


def wait(timeout=5):
    if not wait_event.is_set():
        result = wait_event.wait(timeout)
        if not result:
            raise Exception(
                f"Timeout waiting for event: {wait_event_str}"
            )


def grbl_callback(eventstring, data, verbose):
    if verbose:
        logging.info(f"GRBL callback: {eventstring} {data}")

    if eventstring == "on_rx_buffer_percent" and data[0] == 0:
        event_grbl_rx_buffer_percent_zero.set()

    if eventstring == wait_event_str:
        if wait_data_0 is None or data[0] == wait_data_0:
            wait_event.set()


class ASRSTcpClient(sorter.network.tcp_client.TcpClient):
    def __init__(
        self,
        host,
        port,
        name,
        type,
        retry_connection,
        auto_reconnect,
        asrs_service,
    ):
        super().__init__(host, port, name, type, retry_connection, auto_reconnect)
        self.asrs_service: ASRSService = asrs_service

    def event_msg_received(self, msg):
        part_list = str(msg, "utf-8").split(" ")

        try:
            # classification result
            if part_list[0] == "CLR":
                object_id = int(part_list[1])
                predicted_class = part_list[2]
                probability = float(part_list[3])
                uniqueness = float(part_list[4])
                average_process_time_sec = float(part_list[5])
                pred_low_serialized = part_list[6]
                pred_high_serialized = part_list[7]
                pred_low_list = sorter.classification_service.classification_service.ClassificationService.deserialize(
                    pred_low_serialized
                )
                pred_high_list = sorter.classification_service.classification_service.ClassificationService.deserialize(
                    pred_high_serialized
                )
                logging.info(
                    f"Received classification result - id: {object_id} pc: {predicted_class}"
                    " prob: {probability*100:.0f}% uniqueness: {uniqueness:.0f}"
                )
                self.asrs_service.run_job()

        except ValueError:
            logging.error(
                "Decoding network message error - could be malformed/entangled messages"
            )


class ASRSService:
    def __init__(
        self,
        host: str,
        disable_network,
        disable_device,
        disable_auto_homing,
        verbose,
    ) -> None:
        # network thread
        if not disable_network:
            self.tcp_client = ASRSTcpClient(
                host,
                5005,
                "ASRSService",
                "ASRSService",
                retry_connection=True,
                auto_reconnect=True,
                asrs_service=self,
            )
            self.tcp_client.start()
        else:
            self.tcp_client = None

        # GRBl connection
        self.disable_device = disable_device
        self.device_path = "/dev/serial/by-path/pci-0000:00:14.0-usb-0:2:1.0-port0"
        self.grbl = GrblStreamer(lambda e, *data: grbl_callback(e,data,verbose))
        self.grbl.setup_logging()

        # simulation mode
        if not self.disable_device:
            self.grbl.cnect(self.device_path, 115200)
        else:
            logging.info("GRBL Streamer Simulation mode enabled.")
            self.grbl.target = "simulator"

        self.grbl.hash_state_requested = True

        # wait connection to complete before start polling
        time.sleep(2)
        self.grbl.poll_start()

        # auto-homing
        if not disable_auto_homing:
            logging.warning("⚠️  Machine will auto-home in 5 seconds")
            logging.warning("Ensure machine is clear")
            for i in range(5, 0, -1):
                logging.warning(f"{i} ...")
                time.sleep(1)
            self.homing()
        
        logging.info("Service ready for usage.")

    def stop(self):
        self.grbl.disconnect()
        if self.tcp_client is not None:
            self.tcp_client.stop()

    def notify(self, notification_type, notification_msg):
        pass

    def homing(self):
        # TODO: Class must be blocked before homing completed

        wait_prepare("on_stateupdate", "Idle")
        self.grbl.homing()
        logging.info("Waiting for homing completion ...")
        wait(timeout=30)
        logging.info("done.")

        # G21 ; millimeters
        # G90 ; absolute coordinate
        # G92 X0 Y0 Z0 ; set origin
        # G17 ; XY plane
        for msg in ["G21", "G90", "G92X0Y0Z0", "G17"]:
            logging.info(f"Sending {msg} ...")
            wait_prepare("on_write", msg + "\n")
            self.grbl.send_immediately(msg)
            wait()
            logging.info("confirmed.")

    def goto(self):
        logging.info("Starting motion ...")
        wait_prepare("on_standstill", None)
        self.grbl.send_immediately("G0 X100 Y100")
        logging.info("Waiting for motion completion ...")
        wait()
        logging.info("Motion complete.")

    def run_job(self):

        home_x = 0
        home_y = 500

        lowered = 20
        x = random.randint(0, 1150)
        y = random.randint(0, 500 - lowered)

        # prepare G-CODE sequence

        # retrival
        self.grbl.write(f"G0X{x}Y{y+lowered}")
        self.grbl.write(f"G0X{x}Y{y+lowered}Z-10") # move in
        self.grbl.write(f"G1X{x}Y{y}F5000")  # move up slow
        self.grbl.write(f"G0X{x}Y{y}Z0") # move out

        # move to loading position
        self.grbl.write(f"G0X{home_x}Y{home_y}")
        self.grbl.write(f"G0X{home_x}Y{home_y}Z-20") # move in
        self.grbl.write(f"G0X{home_x}Y{home_y}Z0") # move out
        
        # storage
        self.grbl.write(f"G0X{x}Y{y}")
        self.grbl.write(f"G0X{x}Y{y}Z-10") # move in
        self.grbl.write(f"G1X{x}Y{y+lowered}F5000")  # move up slow
        self.grbl.write(f"G0X{x}Y{y+lowered}Z0") # move out
        
        # trigger motion
        if not self.disable_device:
            wait_prepare("on_standstill", None)
        else:
            wait_prepare("on_simulation_finished", None)

        self.grbl.job_run()
        wait(timeout=20)
        logging.info("Job complete.")