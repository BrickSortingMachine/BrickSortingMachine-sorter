import test_helpers
from test_amqtt_broker import AmqttBrokerThread


class MqttTestCase(test_helpers.BaseTest):
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
        self.setup_logging()

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
        if self.broker_thread and self.broker_thread.is_alive():
            print("\n(tearDown) Stopping AMQTT broker...")
            self.broker_thread.stop()
            # Wait for the thread to finish
            self.broker_thread.join(timeout=5)

            if self.broker_thread.is_alive():
                print(
                    "(tearDown) WARNING: Timed out waiting for broker thread to stop."
                )
            else:
                print("(tearDown) Broker stopped and thread joined.")
        self.broker_thread = None

        self.assert_threads_stopped()
