import json
import logging
import pathlib
import threading
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
    def test_general_std(self):
        self.main_test_general(enable_mqtt=False)

    def test_general_mqtt(self):
        self.main_test_general(enable_mqtt=True)

    def main_test_general(self, enable_mqtt):
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
            enable_mqtt=enable_mqtt,
        )
        time.sleep(1)

        # assert test data available
        path = pathlib.Path("rec_2023-08-09_21-38-43") / "frame_000548.jpg"
        if not ("data" / path).is_file():
            raise Exception(
                "Test data is not available - run tools/download_unpack_test_data.py"
            )

        mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

        def mqtt_on_connect(client, userdata, flags, reason_code, properties):
            if reason_code.is_failure:
                raise Exception(
                    f"Failed to connect to MQTT broker: {reason_code}. Will retry."
                )
            else:
                client.subscribe("bricksortingmachine/classification/result", qos=1)

        mqtt_last_classification_result = None

        def mqtt_on_message(client, userdata, msg):
            nonlocal mqtt_last_classification_result
            payload = json.loads(msg.payload.decode())
            logging.info(f"MQTT message received: {msg.topic} {payload}")
            if msg.topic == "bricksortingmachine/classification/result":
                mqtt_last_classification_result = payload

        mqtt_client.on_connect = mqtt_on_connect
        mqtt_client.on_message = mqtt_on_message
        mqtt_client.connect(self.broker_host, self.broker_port)
        mqtt_client.loop_start()

        for i in range(1):
            # send classification request
            s.broadcast(b"CLF 5 " + bytes(str(path), "utf-8"))
            payload = {
                "object_id": i,
                "image_path": str(path),
            }
            mqtt_client.publish(
                "bricksortingmachine/classification/request",
                json.dumps(payload),
                qos=2,
            )

            time.sleep(
                1.5
            )  # classification waits 1s artificially before sending result

            if not enable_mqtt:
                self.assertEqual(
                    "plate1x", s.get_handler_list()[0].last_classification_result
                )
            else:
                self.assertIsNotNone(mqtt_last_classification_result)
                self.assertEqual(
                    "plate1x", mqtt_last_classification_result["predicted_class"]
                )
                self.assertEqual(i, mqtt_last_classification_result["object_id"])
                mqtt_last_classification_result = None

        # stop network
        time.sleep(1)
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        cs.stop()
        s.stop()
        time.sleep(0.5)

    def test_mqtt_status(self):
        """
        Tests the MQTT online/offline status messages.
        """

        time.sleep(2)

        self.setup_logging()

        # Use a threading Event to signal when the message is received
        message_received_event = threading.Event()
        received_message = None

        subscriber_connected_event = threading.Event()

        def on_message(client, userdata, msg):
            nonlocal received_message
            logging.info(f"MQTT message received: {msg.topic} {msg.payload}")
            received_message = msg
            message_received_event.set()

        def on_client_connect(client, userdata, flags, reason_code, properties):
            if reason_code.is_failure:
                raise Exception(
                    f"Failed to connect to MQTT broker: {reason_code}. Will retry."
                )
            else:
                logging.info("MQTT client connected successfully")
                subscriber_connected_event.set()

                # subscribe to events
                client.subscribe("bricksortingmachine/classification/status", qos=1)

        # Subscriber to listen for the status message
        subscriber = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, client_id="subscriber"
        )
        subscriber.on_message = on_message
        subscriber.on_connect = on_client_connect

        time.sleep(0.5)
        logging.info("Subscriber trying to connect ...")
        subscriber.connect(self.broker_host, self.broker_port)
        subscriber.loop_start()
        time.sleep(0.5)

        logging.info("Waiting 4s for subscriber connected ...")
        self.assertTrue(
            subscriber_connected_event.wait(timeout=4),
            "Subscriber not connected successfully",
        )

        # Instantiate the service, which should publish "online"
        cs = sorter.classification_service.classification_service.ClassificationService(
            host=self.broker_host,
            port=self.broker_port,
            enable_cnn=False,
            model_fp="models/moved_crop_centrally.h5",
            enable_mqtt=True,
        )

        # Wait for the message to be received, with a timeout
        logging.info("Waiting 4s for status message received ...")
        message_received = message_received_event.wait(timeout=4)
        self.assertTrue(
            message_received, "Did not receive MQTT status message in time."
        )

        # Assert the "online" message content
        self.assertIsNotNone(received_message)
        self.assertEqual(
            received_message.topic, "bricksortingmachine/classification/status"
        )
        self.assertEqual(received_message.payload, b"online")
        self.assertEqual(received_message.qos, 1)

        # --- Verify retained message ---
        message_received_event.clear()
        received_message = None

        # Create a new subscriber that should get the retained message immediately
        retained_subscriber = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, client_id="retained_subscriber"
        )
        retained_subscriber.on_message = on_message

        def on_retained_subscriber_connect(
            client, userdata, flags, reason_code, properties
        ):
            client.subscribe("bricksortingmachine/classification/status", qos=1)

        retained_subscriber.on_connect = on_retained_subscriber_connect
        retained_subscriber.connect(self.broker_host, self.broker_port)
        retained_subscriber.loop_start()
        retained_subscriber.daemon = True

        message_received = message_received_event.wait(timeout=2)
        self.assertTrue(
            message_received, "Did not receive retained MQTT status message."
        )

        self.assertIsNotNone(received_message)
        self.assertEqual(received_message.payload, b"online")

        # Cleanup
        retained_subscriber.loop_stop()
        retained_subscriber.disconnect()
        subscriber.loop_stop()
        subscriber.disconnect()
        cs.stop()

    def test_status_last_will_ungraceful_disconnect(self):
        """
        Last Will on ungraceful disconnect
        """
        self.setup_logging()

        # Use a threading Event to signal when the message is received
        message_received_event = threading.Event()
        received_message = None

        def on_message(client, userdata, msg):
            nonlocal received_message
            logging.info(f"MQTT message received: {msg.topic} {msg.payload}")
            # We are expecting two messages: "online" and then "offline"
            if msg.payload == b"offline":
                received_message = msg
                message_received_event.set()

        # Subscriber to listen for the status message
        subscriber = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        subscriber.on_message = on_message

        def on_subscriber_connect(client, userdata, flags, reason_code, properties):
            client.subscribe("bricksortingmachine/classification/status", qos=1)

        subscriber.on_connect = on_subscriber_connect
        subscriber.connect(self.broker_host, self.broker_port)
        subscriber.loop_start()
        time.sleep(0.1)

        # Instantiate the service, which should publish "online"
        cs = sorter.classification_service.classification_service.ClassificationService(
            host="127.0.0.1",
            port=self.broker_port,
            enable_cnn=False,
            model_fp="models/moved_crop_centrally.h5",
            enable_mqtt=True,
        )
        time.sleep(0.5)  # Give time for the "online" message to be sent

        # Simulate an ungraceful disconnect by closing the socket
        logging.info("Simulating ungraceful disconnect ...")
        cs.mqtt_client._sock.close()

        # Wait for the LWT "offline" message to be received
        message_received = message_received_event.wait(timeout=2)
        self.assertTrue(
            message_received, "Did not receive LWT 'offline' message in time."
        )

        # Assert the "offline" message content
        self.assertIsNotNone(received_message)
        self.assertEqual(
            received_message.topic, "bricksortingmachine/classification/status"
        )
        self.assertEqual(received_message.payload, b"offline")

        # Cleanup
        subscriber.loop_stop()
        subscriber.disconnect()
        cs.stop()

    def test_mqtt_status_normal_disconnect(self):
        """
        Last Will on normal disconnect
        """
        self.setup_logging()

        # Use a threading Event to signal when the message is received
        message_received_event = threading.Event()
        received_message = None

        def on_message(client, userdata, msg):
            nonlocal received_message
            logging.info(f"MQTT message received: {msg.topic} {msg.payload}")
            # We are expecting two messages: "online" and then "offline"
            if msg.payload == b"offline":
                received_message = msg
                message_received_event.set()

        # Subscriber to listen for the status message
        subscriber = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        subscriber.on_message = on_message

        def on_subscriber_connect(client, userdata, flags, reason_code, properties):
            client.subscribe("bricksortingmachine/classification/status", qos=1)

        subscriber.on_connect = on_subscriber_connect
        subscriber.connect(self.broker_host, self.broker_port)
        subscriber.loop_start()
        time.sleep(0.1)

        # Instantiate the service, which should publish "online"
        cs = sorter.classification_service.classification_service.ClassificationService(
            host="127.0.0.1",
            port=self.broker_port,
            enable_cnn=False,
            model_fp="models/moved_crop_centrally.h5",
            enable_mqtt=True,
        )
        time.sleep(0.5)  # Give time for the "online" message to be sent

        # TODO: Check "online" message was recived

        # Normal disconnect
        logging.info("Normal disconnect ...")
        cs.stop()

        # Wait for the LWT "offline" message to be received
        message_received = message_received_event.wait(timeout=2)
        self.assertTrue(
            message_received, "Did not receive LWT 'offline' message in time."
        )

        # Assert the "offline" message content
        self.assertIsNotNone(received_message)
        self.assertEqual(
            received_message.topic, "bricksortingmachine/classification/status"
        )
        self.assertEqual(received_message.payload, b"offline")

        # Cleanup
        subscriber.loop_stop()
        subscriber.disconnect()
