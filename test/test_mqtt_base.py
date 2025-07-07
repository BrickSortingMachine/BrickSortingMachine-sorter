import socket
import subprocess
import time
import unittest
from contextlib import closing


def is_port_open(port):
    """Helper function to check if a local port is open and listening."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.settimeout(1)
        return sock.connect_ex(("localhost", port)) == 0


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
        self.broker_process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        # Wait for the broker to be ready to accept connections
        max_wait_time = 5  # seconds
        start_time = time.time()
        while not is_port_open(self.broker_port):
            if self.broker_process.poll() is not None:
                raise RuntimeError("Mosquitto broker failed to start.")
            if time.time() - start_time > max_wait_time:
                # Clean up the process before raising the error
                self.broker_process.terminate()
                stdout, stderr = self.broker_process.communicate()
                raise TimeoutError(
                    "Timed out waiting for Mosquitto broker to start."
                    f"\nStdout: {stdout}\nStderr: {stderr}"
                )
            time.sleep(0.05)

        # mosquitte sends "Error:" msg in case e.g. port is already bound
        time.sleep(0.5)
        stdout, stderr = self.broker_process.communicate()
        if "Error" in stdout or "Error" in stderr:
            raise RuntimeError(
                f"Mosquitto broker failed with error.\nStdout: {stdout}\nStderr: {stderr}"
            )

        print("Mosquitto broker started successfully.")

    def tearDown(self):
        """
        Called after each test method.
        Stops the Mosquitto broker subprocess.
        """
        if self.broker_process:
            print("\n(tearDown) Stopping Mosquitto broker...")
            self.broker_process.terminate()
            self.broker_process.wait()  # Ensure the process is fully terminated
