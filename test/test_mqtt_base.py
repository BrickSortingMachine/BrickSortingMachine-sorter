import unittest

from test_amqtt_broker import AmqttBrokerThread  # Import our new class


class MqttTestCase(unittest.TestCase):
    """
    A base test case that starts and stops an in-process amqtt broker
    for each test
    """

    broker_thread = None

    def setUp(self):
        """
        Called before each test method.
        Starts the amqtt broker in a separate thread on a fixed port.
        """
        print("\n(setUp) Starting AMQTT broker for test...")
        self.broker_host = "localhost"
        self.broker_port = 1884
        self.broker_thread = AmqttBrokerThread(
            host=self.broker_host, port=self.broker_port
        )
        self.broker_thread.start()

        # Wait for the broker to signal that it's ready.
        started = self.broker_thread.started_event.wait(timeout=5)
        if not started:
            raise TimeoutError("Timed out waiting for AMQTT broker to start.")

        print(f"(setUp) Broker is ready on {self.broker_host}:{self.broker_port}")

    def tearDown(self):
        """
        Called after each test method.
        Stops the amqtt broker thread.
        """
        if self.broker_thread:
            print("\n(tearDown) Stopping AMQTT broker...")
            self.broker_thread.stop()
            print("(tearDown) Broker stopped.")
