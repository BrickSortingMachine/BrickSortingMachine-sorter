import logging

import sorter.network.tcp_client
from grbl_streamer import GrblStreamer

import time
import threading



event_grbl_rx_buffer_percent_zero = threading.Event()

wait_event_str = None
wait_data_0 = None
wait_event = threading.Event()


def wait_prepare(event_str, data_0=None):
    global wait_event
    global wait_event_str
    global wait_data_0
    wait_event.clear()
    wait_event_str = event_str
    wait_data_0 = data_0

def wait():
    if not wait_event.is_set():
        wait_event.wait()


def grbl_callback(eventstring, *data):
    args = []
    for d in data:
        args.append(str(d))
    logging.info("GRBL CALLBACK: event={}".format(eventstring.ljust(30), ", ".join(args)))
    logging.info(data)

    if eventstring == "on_rx_buffer_percent" and data[0] == 0:
        logging.info("Received event_grbl_rx_buffer_percent_zero")
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
            # notification request
            if part_list[0] == "NTF":
                logging.info(f"Received notification request - msg: {msg}")
                notification_type = part_list[1]
                notification_msg = " ".join(part_list[2:])
                self.asrs_service.notify(notification_type, notification_msg)
        except Exception:
            logging.error(
                "Decoding network message error - could be malformed/entangled messages"
            )


class ASRSService:
    def __init__(
        self, host: str, disable_network,
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

        # star grbl stream
        self.device_path = "/dev/serial/by-path/pci-0000:00:14.0-usb-0:2:1.0-port0"
        self.grbl = GrblStreamer(grbl_callback)
        self.grbl.setup_logging()
        self.grbl.cnect(self.device_path, 115200)

        self.grbl.hash_state_requested = True

        logging.info("waiting")
        time.sleep(2)
        logging.info("go")
        self.poll_start()
        
        #
    
    def poll_start(self):
        self.grbl.poll_start()

    def stop(self):
        self.grbl.disconnect()
        if self.tcp_client is not None:
            self.tcp_client.stop()

    def notify(self, notification_type, notification_msg):
        pass

    def homing(self):
        # TODO: Class must be blocked before homing completed

        logging.info("Homing requested ...")
        wait_prepare("on_rx_buffer_percent", 0)
        self.grbl.homing()
        logging.info("Homing waiting for completion ...")
        wait()
        logging.info("Completed.")

        # G21 ; millimeters
        # G90 ; absolute coordinate
        # G92 X0 Y0 Z0 ; set origin
        # G17 ; XY plane

        for msg in ["G21", "G90", "G92X0Y0Z0", "G17"]:
            logging.info(f"Sending {msg} ...")
            wait_prepare("on_write", msg+"\n")
            self.grbl.send_immediately(msg)
            logging.info("waiting ...")
            wait()
            logging.info("completed ...")
    
    def goto(self):
        logging.info("Starting motion ...")
        wait_prepare("on_rx_buffer_percent", 0)
        self.grbl.send_immediately("G0 X100 Y100")
        logging.info("Waiting for motion completion ...")
        wait()
        logging.info("Motion complete.")
