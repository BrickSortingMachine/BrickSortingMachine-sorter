import time

import paho.mqtt.client as mqtt
import test_mqtt_base


class TestMyServiceCommunication(test_mqtt_base.MqttTestCase):
    def test_publish_and_subscribe(self):
        """
        A sample test to verify a message can be published and received.
        """
        # This test will automatically have a clean broker running,
        # thanks to the setUp method in MqttTestCase

        received_message = None

        def on_message(client, userdata, msg):
            nonlocal received_message
            print("MQTT message received")
            received_message = msg.payload.decode()

        # Set up a subscriber
        subscriber = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id="test_receiver",
            clean_session=False,
        )
        subscriber.on_message = on_message
        subscriber.connect(self.broker_host, self.broker_port)
        subscriber.loop_start()
        subscriber.subscribe("my/test/topic")

        # Publish a message
        publisher = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id="test_sender",
            clean_session=False,
        )
        publisher.connect(self.broker_host, self.broker_port)
        publisher.loop_start()
        publisher.publish("my/test/topic", "hello world", qos=2)
        time.sleep(2)  # Give time for message to be processed

        publisher.loop_stop()
        publisher.disconnect()

        subscriber.loop_stop()
        subscriber.disconnect()

        # Assert that the message was received correctly
        self.assertEqual(received_message, "hello world")
