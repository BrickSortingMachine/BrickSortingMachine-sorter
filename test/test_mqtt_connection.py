import time

import paho.mqtt.client as mqtt
import test_mqtt_base


class TestMyServiceCommunication(test_mqtt_base.MqttTestCase):
    def test_publish_and_subscribe(self):
        """
        A sample test to verify a message can be published and received.
        """
        # This test will automatically have a clean broker running,
        # thanks to the setUp method in MqttTestCase.

        received_message = None

        def on_message(client, userdata, msg):
            nonlocal received_message
            received_message = msg.payload.decode()

        # Set up a subscriber
        subscriber = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        subscriber.on_message = on_message
        subscriber.connect("localhost", self.broker_port)
        subscriber.subscribe("my/test/topic")
        subscriber.loop_start()

        # Publish a message
        publisher = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        publisher.connect("localhost", self.broker_port)
        publisher.publish("my/test/topic", "hello world")
        publisher.disconnect()

        time.sleep(0.5)  # Give time for message to be processed

        subscriber.loop_stop()
        subscriber.disconnect()

        # Assert that the message was received correctly
        self.assertEqual(received_message, "hello world")
