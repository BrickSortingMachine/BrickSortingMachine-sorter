import unittest
import subprocess
import time
import socket
from contextlib import closing

def is_port_open(port):
    """Helper function to check if a local port is open and listening."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.settimeout(1)
        return sock.connect_ex(('localhost', port)) == 0

class MqttTestCase(unittest.TestCase):
    """
    A base test case that starts and stops a Mosquitto MQTT broker
    for each test.
    """
    broker_process = None
    broker_port = 1883

    def setUp(self):
        """
        Called before each test method.
        Starts the Mosquitto broker subprocess.
        """
        print("\n(setUp) Starting Mosquitto broker for test...")
        command = ["mosquitto", "-p", str(self.broker_port)]
        
        # Start the broker process
        self.broker_process = subprocess.Popen(command)

        # Wait for the broker to be ready to accept connections
        max_wait_time = 5  # seconds
        start_time = time.time()
        while not is_port_open(self.broker_port):
            if self.broker_process.poll() is not None:
                raise RuntimeError("Mosquitto broker failed to start.")
            if time.time() - start_time > max_wait_time:
                # Clean up the process before raising the error
                self.broker_process.terminate()
                self.broker_process.wait()
                raise TimeoutError("Timed out waiting for Mosquitto broker to start.")
            time.sleep(0.05)
        print("Mosquitto broker started successfully.")

    def tearDown(self):
        """
        Called after each test method.
        Stops the Mosquitto broker subprocess.
        """
        if self.broker_process:
            print("\n(tearDown) Stopping Mosquitto broker...")
            self.broker_process.terminate()
            self.broker_process.wait() # Ensure the process is fully terminated


from test_mqtt_base import MqttTestCase
import paho.mqtt.client as mqtt
import time

class TestMyServiceCommunication(MqttTestCase):

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

        time.sleep(0.5) # Give time for message to be processed

        subscriber.loop_stop()
        subscriber.disconnect()

        # Assert that the message was received correctly
        self.assertEqual(received_message, "hello world")
