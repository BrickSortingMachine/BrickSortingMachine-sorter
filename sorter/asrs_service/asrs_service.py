import logging

import sorter.network.tcp_client


class ASRSTcpClient(sorter.network.tcp_client.TcpClient):
    def __init__(
        self,
        host,
        port,
        name,
        type,
        retry_connection,
        auto_reconnect,
        notificaiton_service,
    ):
        super().__init__(host, port, name, type, retry_connection, auto_reconnect)
        self.notificaiton_service: NotificationService = notificaiton_service

    def event_msg_received(self, msg):
        part_list = str(msg, "utf-8").split(" ")

        try:
            # notification request
            if part_list[0] == "NTF":
                logging.info(f"Received notificaiton request - msg: {msg}")
                notification_type = part_list[1]
                notification_msg = " ".join(part_list[2:])
                self.notificaiton_service.notify(notification_type, notification_msg)
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
                notificaiton_service=self,
            )
            self.tcp_client.start()
        else:
            self.tcp_client = None

    def stop(self):
        if self.tcp_client is not None:
            self.tcp_client.stop()

    def notify(self, notification_type, notification_msg):
        pass
