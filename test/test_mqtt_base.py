import logging
import os
import secrets
import time

import test_helpers
from sorter.broker.mqtt_broker import MqttBrokerThread


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

        # reduce amqtt debug logging
        logging.getLogger("amqtt").setLevel(logging.WARNING)
        logging.getLogger("amqtt.broker").setLevel(logging.WARNING)
        logging.getLogger("transitions.core").setLevel(logging.WARNING)

        self.broker_host = "localhost"
        self.broker_port = 1884
        session_secret = secrets.token_hex(16)
        os.environ["SESSION_SECRET"] = session_secret

        self.broker_thread = MqttBrokerThread(
            host=self.broker_host,
            port=self.broker_port,
            session_secret=session_secret,
            sys_interval=0,
        )
        self.broker_thread.start()

        # Wait for the broker to signal that it's ready.
        started = self.broker_thread.started_event.wait(timeout=5)
        if not started:
            raise TimeoutError("Timed out waiting for AMQTT broker to start.")

        logging.info(
            f"(setUp) aMQTT broker is ready on {self.broker_host}:{self.broker_port}"
        )

    def tearDown(self):
        """
        Called after each test method.
        Stops the amqtt broker thread.
        """
        if self.broker_thread and self.broker_thread.is_alive():
            logging.info("(tearDown) Stopping AMQTT broker...")
            self.broker_thread.stop()
            # Wait for the thread to finish
            self.broker_thread.join(timeout=5)

            if self.broker_thread.is_alive():
                raise TimeoutError(
                    "(tearDown) WARNING: Timed out waiting for broker thread to stop."
                )
            else:
                logging.info("(tearDown) Broker stopped and thread joined.")
        self.broker_thread = None

        if "SESSION_SECRET" in os.environ:
            del os.environ["SESSION_SECRET"]

        time.sleep(0.5)

        self.assert_threads_stopped()
