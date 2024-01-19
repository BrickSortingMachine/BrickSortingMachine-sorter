import logging

import sorter.classification_service.classification_service
import sorter.network.tcp_client
import sorter.serial_service.serial_connection_manager
import sorter.serial_service.slide_serial_connection_handler


class SSTcpClient(sorter.network.tcp_client.TcpClient):
    def __init__(
        self, host, port, name, type, retry_connection, auto_reconnect, serial_service
    ):
        super().__init__(host, port, name, type, retry_connection, auto_reconnect)
        self.serial_service: SerialService = serial_service

    def event_msg_received(self, msg):
        part_list = str(msg, "utf-8").split(" ")

        logging.info(f'SSTcpClient: Received message "{msg}"')

        # classification result
        if part_list[0] == "CLR":
            logging.info(f"Received classification result - msg: {msg}")
            predicted_class = part_list[2]
            pred_low_serialized = part_list[6]
            pred_high_serialized = part_list[7]
            pred_low_list = sorter.classification_service.classification_service.ClassificationService.deserialize(
                pred_low_serialized
            )
            pred_high_list = sorter.classification_service.classification_service.ClassificationService.deserialize(
                pred_high_serialized
            )
            self.serial_service.event_receive_classification_result(
                predicted_class, pred_low_list, pred_high_list
            )


class SerialService:
    def __init__(self, host, disable_network, max_iterations=None) -> None:
        # serial
        self.manager = self.create_connection_manager(max_iterations)
        self.slide = (
            sorter.serial_service.slide_serial_connection_handler.SlideSerialConnectionHandler()
        )
        self.manager.register_handler("slide-controller", self.slide)

        # network
        self.disable_network = disable_network
        if not self.disable_network:
            self.tcp_client = SSTcpClient(
                host,
                5005,
                "SerialService",
                "SerialService",
                retry_connection=True,
                auto_reconnect=True,
                serial_service=self,
            )
            self.tcp_client.start()
        else:
            self.tcp_client = None

    def stop(self):
        self.slide.stop()
        self.tcp_client.stop()

    def create_connection_manager(self, max_iterations):
        return sorter.serial_service.serial_connection_manager.SerialConnectionManager(
            max_iterations
        )

    def event_receive_classification_result(
        self, predicted_class, pred_low_list, pred_high_list
    ):
        self.slide.event_receive_classification_result(
            predicted_class, pred_low_list, pred_high_list
        )
