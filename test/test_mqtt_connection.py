import logging
import os
import threading
import time

import paho.mqtt.client as mqtt
import test_mqtt_base


class TestMyServiceCommunication(test_mqtt_base.MqttTestCase):
    def test_publish_and_subscribe(self):
        """
        A sample test to verify a message can be published and received.
        """
        received_message = None

        def on_message(client, userdata, msg):
            nonlocal received_message
            print("MQTT message received")
            received_message = msg.payload.decode()

        # Set up a subscriber
        subscriber = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
        )
        subscriber.on_message = on_message

        def on_subscriber_connect(client, userdata, flags, reason_code, properties):
            client.subscribe("my/test/topic")

        subscriber.on_connect = on_subscriber_connect
        subscriber.username_pw_set("sorter", os.environ.get("SESSION_SECRET"))
        subscriber.connect(self.broker_host, self.broker_port)
        subscriber.loop_start()

        # Publish a message
        publisher = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
        )
        publisher.username_pw_set("sorter", os.environ.get("SESSION_SECRET"))
        publisher.connect(self.broker_host, self.broker_port)
        publisher.loop_start()
        publisher.publish("my/test/topic", "hello world", qos=2)

        time.sleep(0.5)  # Give time for message to be processed

        publisher.loop_stop()
        publisher.disconnect()

        subscriber.loop_stop()
        subscriber.disconnect()

        # Assert that the message was received correctly
        self.assertEqual(received_message, "hello world")

    def test_last_will(self):
        """
        Minimal Last Will and Testament Test
        """
        received_message = None
        offline_msg_received = threading.Event()

        def on_message(client, userdata, msg):
            nonlocal received_message
            received_message = msg.payload.decode()
            logging.info(f"MQTT message received: {received_message}")
            if received_message == "offline":
                offline_msg_received.set()

        def on_mqtt_connect(client, userdata, flags, reason_code, properties):
            if reason_code.is_failure:
                logging.error(
                    f"Failed to connect to MQTT broker: {reason_code}. Will retry."
                )
            else:
                # publish online message
                client.publish(
                    topic="bricksortingmachine/classification/status",
                    payload="online",
                    qos=1,
                    retain=True,
                )

        # Set up a subscriber
        subscriber = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
        )
        subscriber.on_message = on_message

        def subscriber_on_connect(client, userdata, flags, reason_code, properties):
            if not reason_code.is_failure:
                client.subscribe("bricksortingmachine/classification/status")

        subscriber.on_connect = subscriber_on_connect
        subscriber.username_pw_set("sorter", os.environ.get("SESSION_SECRET"))
        subscriber.connect(self.broker_host, self.broker_port)
        subscriber.loop_start()

        # Publish a message
        publisher = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
        )
        publisher.on_connect = on_mqtt_connect
        publisher.username_pw_set("sorter", os.environ.get("SESSION_SECRET"))
        publisher.will_set(
            "bricksortingmachine/classification/status", "offline", 1, True
        )
        publisher.connect(self.broker_host, self.broker_port)
        publisher.loop_start()

        time.sleep(0.5)  # Give time for message to be processed

        # simulate ungraceful disconnect
        logging.info("Forcfull cut-off connection ...")
        publisher._sock.close()

        # wait for last will message "offline"
        self.assertTrue(
            offline_msg_received.wait(timeout=5),
            "Timeout while waiting 5s on last will message",
        )

        publisher.loop_stop()
        publisher.disconnect()

        subscriber.loop_stop()
        subscriber.disconnect()

        # Assert that the message was received correctly
        self.assertEqual(received_message, "offline")
