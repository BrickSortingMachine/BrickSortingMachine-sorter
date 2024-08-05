import base64
import datetime
import json
import logging
import pathlib
import threading
import time
from dataclasses import dataclass

import sorter.classification_service.classification_result
import sorter.classification_service.config
import sorter.network.tcp_client
import sorter.notification_service.notification_client as nc


@dataclass
class QueueItem:
    object_id: int = None
    img_filepath: str = None


class CSTcpClient(sorter.network.tcp_client.TcpClient):
    def __init__(
        self,
        host,
        port,
        name,
        type,
        retry_connection,
        auto_reconnect,
        classification_service,
    ):
        super().__init__(host, port, name, type, retry_connection, auto_reconnect)
        self.classification_service: ClassificationService = classification_service

    def event_msg_received(self, msg):
        part_list = str(msg, "utf-8").split(" ")

        # classification request
        if part_list[0] == "CLF":
            object_id = int(part_list[1])
            filepath = part_list[2]
            logging.info(
                f"Received classification request - id: {object_id} fp: {filepath}"
            )
            self.classification_service.add_queue(object_id, filepath)


class ClassificationService:
    def __init__(self, host, enable_cnn, model_fp) -> None:
        # classifier
        self.enable_cnn = enable_cnn
        if self.enable_cnn:
            import sorter.classification_service.classifier

            assert isinstance(model_fp, pathlib.Path)

            self.classifier = sorter.classification_service.classifier.Classifier(
                model_fp
            )
        self.average_process_time_sec = None

        # classification thread
        self.thread_stop_requested = False
        self.queue_mutex = threading.Lock()
        self.queue_condition = threading.Condition(self.queue_mutex)
        self.queue = []
        self.thread = threading.Thread(target=self.thread_fct)
        self.thread.daemon = True
        self.thread.start()
        self.thread.name = "Classification Service"

        # network thread
        self.tcp_client = CSTcpClient(
            host,
            5005,
            "ClassificationService",
            "ClassificationService",
            retry_connection=True,
            auto_reconnect=True,
            classification_service=self,
        )
        self.tcp_client.start()

        # notification
        self.notification_client = nc.NotificationClient(self.tcp_client)

    def stop(self) -> None:
        # network thread
        self.tcp_client.stop()

        # classification thread
        self.thread_stop_requested = True
        self.queue_mutex.acquire()
        logging.info("Notifying for stop ...")
        self.queue_condition.notify_all()
        self.queue_mutex.release()
        self.thread.join()

    def add_queue(self, object_id, img_filepath):
        self.queue_mutex.acquire()
        logging.info("Adding to queue ...")
        self.queue.append(QueueItem(object_id=object_id, img_filepath=img_filepath))
        logging.info("Notifying ...")
        self.queue_condition.notify_all()
        self.queue_mutex.release()

    def get_result_list(self):
        pass

    def thread_fct(self):
        logging.info("Classifier thread started ...")
        while not self.thread_stop_requested:
            queue_item = None
            self.queue_mutex.acquire()

            logging.info(f"Thread: Checking queue len: {len(self.queue)}")
            if len(self.queue) > 0:
                queue_item: QueueItem = self.queue.pop()
            else:
                logging.info("Thread: Queue empty - going to wait ...")
                self.queue_condition.wait()
                logging.info("Thread: Woke up.")

            self.queue_mutex.release()

            if queue_item is not None:
                logging.info("Thread: Processing ...")
                self.process_queue_item(queue_item)

        logging.info("Classifier thread stopped.")

    def process_queue_item(self, queue_item: QueueItem):
        dt_start = datetime.datetime.now()

        # img path is relative to data_dir
        img_abspath = (
            sorter.classification_service.config.data_dir_path
            / pathlib.Path(queue_item.img_filepath)
        ).resolve()

        if not img_abspath.is_file():
            raise Exception(f"File {img_abspath} does not exist")

        logging.info(f"Predicting {img_abspath} ...")

        # run CNN
        if self.enable_cnn:
            cr = self.classifier.predict(str(img_abspath))
            predicted_class = cr.predicted_class
            probability = cr.probability
            uniqueness = cr.uniqueness
        else:
            predicted_class = "plate1x"
            pred_low_list = [
                {"class": "plate1x", "probability": 1},
                {"class": "brick1x", "probability": 0},
                {"class": "brick2x", "probability": 0},
            ]
            pred_high_list = pred_low_list
            cr = sorter.classification_service.classification_result.ClassificationResult(
                predicted_class=predicted_class,
                predicted_class_high=predicted_class,
                probability=None,
                uniqueness=None,
                prediction_list=[],
                label_data={},
                low_list=pred_low_list,
                high_list=pred_high_list,
            )
            probability = 1
            uniqueness = 100
            time.sleep(1.2)

        logging.info(f"PredictedClass: {predicted_class}")
        dt_end = datetime.datetime.now()
        delta_sec = (dt_end - dt_start).total_seconds()

        if self.average_process_time_sec is None:
            self.average_process_time_sec = delta_sec
        else:
            self.average_process_time_sec = (
                0.7 * self.average_process_time_sec + 0.1 * delta_sec
            )
        logging.info(f"Average Processing Time: {self.average_process_time_sec:.2f}s")

        # skip
        if probability < 0.55 or uniqueness < 0.0:
            predicted_class = "skip"
        if cr.predicted_class != cr.predicted_class_high:
            predicted_class = (
                "inc_" + cr.predicted_class + "_" + cr.predicted_class_high
            )

        # send result to vision
        msg = self.compose_classification_result_message(
            queue_item.object_id,
            predicted_class,
            probability,
            uniqueness,
            self.average_process_time_sec,
            cr.low_list[:3],
            cr.high_list[:3],
        )
        logging.info(msg)
        self.tcp_client.send_msg(msg)

        # send notification
        self.notification_client.notify_classification_result(predicted_class)

    @staticmethod
    def compose_classification_result_message(
        object_id,
        predicted_class,
        probability,
        uniqueness,
        average_process_time_sec,
        low_list,
        high_list,
    ):
        pred_low_serialized = ClassificationService.serialize(low_list)
        pred_high_serialized = ClassificationService.serialize(high_list)
        msg = f"CLR {object_id:d} {predicted_class} {probability} {uniqueness} {average_process_time_sec} {pred_low_serialized} {pred_high_serialized}"
        return bytes(msg, "utf-8")

    @staticmethod
    def serialize(d) -> str:
        s = str(base64.b64encode(bytes(json.dumps(d), "utf-8")), "utf-8")
        assert " " not in s
        return s

    @staticmethod
    def deserialize(s: str):
        return json.loads(str(base64.b64decode(bytes(s, "utf-8")), "utf-8"))
