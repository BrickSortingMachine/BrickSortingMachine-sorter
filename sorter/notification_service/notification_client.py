import logging

import sorter.network.tcp_client


class NotificationClient:
    def __init__(self, tcp_client: sorter.network.tcp_client.TcpClient) -> None:
        self.tcp_client = tcp_client

    def notify_part_scanned(self):
        self.send(b"NTF part_scanned")

    def notify_scanner_inhibition_ended(self):
        self.send(b"NTF scanner_inhibition_ended")

    def notify_soft_estop(self, enabled: bool):
        msg = b"True" if enabled else b"False"
        self.send(b"NTF soft_estop " + msg)

    def notify_classification_result(self, predicted_class: str):
        self.send(b"NTF classification_result " + bytes(predicted_class, "utf-8"))

    def notify_timeout_max_non_busy(self, sec_since_last_busy):
        msg = b"NTF timeout_max_non_busy %d" % sec_since_last_busy
        self.send(msg)

    def notify_double_part_scanned(self):
        msg = b"NTF double_part_scanned"
        self.send(msg)

    def send(self, msg):
        if self.tcp_client is None:
            logging.warning("TCPClient not available")
            return

        if self.tcp_client.get_connected():
            self.tcp_client.send_msg(msg)
