import logging

import sorter.network.tcp_client
from grbl_streamer import GrblStreamer


def grbl_callback(eventstring, *data):
    args = []
    for d in data:
        args.append(str(d))
    logging.info("GRBL CALLBACK: event={}".format(eventstring.ljust(30), ", ".join(args)))


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
        self.grbl.poll_start()

    def stop(self):
        self.grbl.disconnect()
        if self.tcp_client is not None:
            self.tcp_client.stop()

    def notify(self, notification_type, notification_msg):
        pass

    def stream_gcode(self):
        gcode = "G0 X10 Y10\nG0 X0 Y0\n"
        self.grbl.stream(gcode)
