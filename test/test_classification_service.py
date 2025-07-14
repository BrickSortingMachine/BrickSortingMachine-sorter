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

    def test_mqtt_status(self):
        """
        Tests the MQTT online/offline status messages.
        """
        self.setup_logging()

        # Use a threading Event to signal when the message is received
        message_received_event = threading.Event()
        received_message = None

        def on_message(client, userdata, msg):
            nonlocal received_message
            logging.info(f"MQTT message received: {msg.topic} {msg.payload}")
            received_message = msg
            message_received_event.set()

        # Subscriber to listen for the status message
        subscriber = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, client_id="subscriber"
        )
        subscriber.on_message = on_message
        subscriber.connect(self.broker_host, self.broker_port)
        subscriber.subscribe("bricksortingmachine/classification/status", qos=1)
        subscriber.loop_start()
        time.sleep(0.1)

        # Dummy TCP server that the service needs
        tcp_server = sorter.network.tcp_server.TcpServer(
            "0.0.0.0", 5005, DummyCommandHandler
        )
        tcp_server.start()
        time.sleep(0.1)

        # Instantiate the service, which should publish "online"
        cs = sorter.classification_service.classification_service.ClassificationService(
            host=self.broker_host,
            port=self.broker_port,
            enable_cnn=False,
            model_fp="models/moved_crop_centrally.h5",
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
        retained_subscriber.connect(self.broker_host, self.broker_port)
        retained_subscriber.subscribe(
            "bricksortingmachine/classification/status", qos=1
        )
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
        time.sleep(1)  # Allow time for cs thread to stop
        tcp_server.stop()
        time.sleep(0.5)  # Allow time for threads to stop

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
        subscriber.connect(self.broker_host, self.broker_port)
        subscriber.subscribe("bricksortingmachine/classification/status", qos=1)
        subscriber.loop_start()
        time.sleep(0.1)

        # TCP server
        tcp_server = sorter.network.tcp_server.TcpServer(
            "0.0.0.0", 5005, DummyCommandHandler
        )
        tcp_server.start()
        time.sleep(0.1)

        # Instantiate the service, which should publish "online"
        cs = sorter.classification_service.classification_service.ClassificationService(
            host="127.0.0.1",
            port=self.broker_port,
            enable_cnn=False,
            model_fp="models/moved_crop_centrally.h5",
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
        tcp_server.stop()
        time.sleep(1)

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
        subscriber.connect(self.broker_host, self.broker_port)
        subscriber.subscribe("bricksortingmachine/classification/status", qos=1)
        subscriber.loop_start()
        time.sleep(0.1)

        # TCP server
        tcp_server = sorter.network.tcp_server.TcpServer(
            "0.0.0.0", 5005, DummyCommandHandler
        )
        tcp_server.start()
        time.sleep(0.1)

        # Instantiate the service, which should publish "online"
        cs = sorter.classification_service.classification_service.ClassificationService(
            host="127.0.0.1",
            port=self.broker_port,
            enable_cnn=False,
            model_fp="models/moved_crop_centrally.h5",
        )
        time.sleep(0.5)  # Give time for the "online" message to be sent

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
        tcp_server.stop()
        time.sleep(1)
