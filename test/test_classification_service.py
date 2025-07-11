import json
import logging
import pathlib
import time

import paho.mqtt.client as mqtt
import test_helpers
import test_mqtt_base

import sorter.classification_service.classification_service
import sorter.network.tcp_server


class DummyCommandHandler(sorter.network.tcp_server.RequestHandler):
    def __init__(self, request, client_address, server) -> None:
        self.belt_busy = None
        self.belt_busy_frame_index = None
        self.last_classification_result = None
        super().__init__(request, client_address, server)

    def process_custom_command(self, message):
        command = message[:3]

        # CLR - Classification Result
        if command == b"CLR":
            # b'BST busy 57'
            part_list = str(message, "utf-8").split(" ")
            object_id = int(part_list[1])
            predicted_class = part_list[2]
            logging.info(
                f"Received command CLR - id: {object_id} prediction: {predicted_class}"
            )
            self.last_classification_result = predicted_class

        elif command == b"NTF":
            logging.info(f"Received notification command: {message}")

        else:
            raise Exception("Received unsupported command: " "%s" "" % command)


class ClassificationServiceTest(test_mqtt_base.MqttTestCase, test_helpers.BaseTest):
    def test_general(self):
        """
        General
        """
        self.setup_logging()

        # dummy server
        s = sorter.network.tcp_server.TcpServer("0.0.0.0", 5005, DummyCommandHandler)
        s.start()
        time.sleep(1)

        cs = sorter.classification_service.classification_service.ClassificationService(
            host="127.0.0.1",
            port=self.broker_port,
            enable_cnn=False,
            model_fp="models/moved_crop_centrally.h5",
        )
        time.sleep(1)

        # assert test data available
        path = pathlib.Path("rec_2023-08-09_21-38-43") / "frame_000548.jpg"
        if not ("data" / path).is_file():
            raise Exception(
                "Test data is not available - run tools/download_unpack_test_data.py"
            )

        publisher = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        publisher.connect(self.broker_host, self.broker_port)
        publisher.loop_start()

        for i in range(1):
            # send classification request
            s.broadcast(b"CLF 5 " + bytes(str(path), "utf-8"))
            payload = {
                "object_id": 5,
                "image_path": str(path),
            }
            publisher.publish(
                "bricksortingmachine/classification/request",
                json.dumps(payload),
                qos=2,
            )

            time.sleep(
                1.5
            )  # classification waits 1s artificially before sending result
            self.assertEqual(
                "plate1x", s.get_handler_list()[0].last_classification_result
            )

        # stop network
        time.sleep(1)
        publisher.loop_stop()
        publisher.disconnect()
        cs.stop()
        s.stop()
        time.sleep(0.5)
