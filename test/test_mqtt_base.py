import socket
import subprocess
import time
import unittest
import threading
from contextlib import closing


def _read_stream(stream, output_list):
    """Reads a stream line-by-line and stores it in output_list."""
    # The `iter(stream.readline, '')` part reads lines until the stream is closed
    for line in iter(stream.readline, ''):
        output_list.append(line)
    stream.close()


def is_port_open(port):
    """Helper function to check if a local port is open and listening."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.settimeout(1)
        return sock.connect_ex(("localhost", port)) == 0


class MqttTestCase(unittest.TestCase):
    """
    A base test case that starts and stops a Mosquitto MQTT broker
    for each test, using threads to monitor for startup errors.
    """

    broker_process = None
    broker_port = 1883

    def setUp(self):
        """
        Called before each test method.
        Starts the Mosquitto broker and background reader threads.
        """
        print("\n(setUp) Starting Mosquitto broker for test...")
        command = ["mosquitto", "-p", str(self.broker_port)]

        try:
            self.broker_process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
        except FileNotFoundError:
            raise Exception("Cannot start mosquitto server - potentially not installed")

        # --- Threaded Reader Setup ---
        # Lists to hold output captured by the threads
        self.stdout_lines = []
        self.stderr_lines = []

        # Create and start non-blocking reader threads
        self.stdout_thread = threading.Thread(
            target=_read_stream, args=(self.broker_process.stdout, self.stdout_lines)
        )
        self.stderr_thread = threading.Thread(
            target=_read_stream, args=(self.broker_process.stderr, self.stderr_lines)
        )
        self.stdout_thread.daemon = True
        self.stderr_thread.daemon = True
        self.stdout_thread.start()
        self.stderr_thread.start()
        # --- End Threading Setup ---

        # --- Wait for Broker and Check for Errors ---
        max_wait_time = 5  # seconds
        start_time = time.time()
        broker_ready = False

        while time.time() - start_time < max_wait_time:
            # Check for an early error message from the background threads
            stderr_output = "".join(self.stderr_lines)
            if "Error" in stderr_output:
                # If an error is found, no need to wait further.
                raise RuntimeError(
                    f"Mosquitto broker failed on startup with error.\nStderr: {stderr_output}"
                )

            # If no error, check if the broker is ready to accept connections
            if is_port_open(self.broker_port):
                print("Mosquitto broker is ready and listening.")
                broker_ready = True
                break  # Success! Exit the loop.

            # Also check if the process died for some other reason
            if self.broker_process.poll() is not None:
                break

            time.sleep(0.05)

        # After the loop, if the broker isn't ready, it's a timeout.
        if not broker_ready:
            stdout = "".join(self.stdout_lines)
            stderr = "".join(self.stderr_lines)
            raise TimeoutError(
                "Timed out waiting for Mosquitto broker to start."
                f"\nStdout: {stdout}\nStderr: {stderr}"
            )

    def tearDown(self):
        """
        Called after each test method.
        Stops the Mosquitto broker subprocess.
        """
        if self.broker_process:
            print("\n(tearDown) Stopping Mosquitto broker...")
            self.broker_process.terminate()
            # Wait for the process to terminate to ensure clean shutdown
            try:
                self.broker_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("Broker did not terminate gracefully, killing.")
                self.broker_process.kill()

            # The threads will exit automatically as the pipes close.
            # You can optionally join them to be sure.
            self.stdout_thread.join()
            self.stderr_thread.join()
