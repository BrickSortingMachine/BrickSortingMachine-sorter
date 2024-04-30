import logging
import time

import sorter.classification_service.classification_service
import sorter.network.tcp_server


class CSCTcpClient(sorter.network.tcp_client.TcpClient):
    def __init__(self, client):
        super().__init__(
            host="127.0.0.1",
            port=5005,
            name="VisionService",
            type="VisionService",
            retry_connection=False,
            auto_reconnect=False,
        )
        self.client: ClassificationServiceClient = client

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
                self.client.receive_classification_result(
                    object_id,
                    predicted_class,
                    probability,
                    uniqueness,
                    average_process_time_sec,
                    pred_low_list,
                    pred_high_list,
                )

        except ValueError:
            logging.error(
                "Decoding network message error - could be malformed/entangled messages"
            )


class ClassificationServiceClient:
    def __init__(self) -> None:
        self.predicted_class = None

    def run(self, path):
        tcp_client = CSCTcpClient(client=self)
        tcp_client.start()
        time.sleep(0.5)
        tcp_client.send_msg(b"CLF 5 " + bytes(str(path), "utf-8"))

        assert self.predicted_class is None
        while True:
            time.sleep(0.1)
            if self.predicted_class is not None:
                break
        logging.info(f"Received class prediction: {self.predicted_class}")
        return self.predicted_class

    def receive_classification_result(
        self,
        object_id,
        predicted_class,
        probability,
        uniqueness,
        average_process_time_sec,
        pred_low_list,
        pred_high_list,
    ):
        self.predicted_class = predicted_class
