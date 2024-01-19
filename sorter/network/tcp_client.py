import logging
import socket
import sys
import threading
import time


class TcpClient:
    def __init__(self, host, port, name, type, retry_connection, auto_reconnect):
        self.host = host
        self.port = port
        self.name = name
        self.type = type
        self.client_thread = None
        self.last_message = None
        self.sock = None
        self.connected = False
        self.thread_active = False
        self.log_received_messages = True
        self.stop_requested = False
        self.retry_connection = retry_connection
        self.auto_reconnect = auto_reconnect

    def event_connected(self):
        """
        Called after connection to server was established - to be overwritten
        by derived detail implementation.
        """
        pass

    def event_msg_received(self, msg):
        """
        Called when message was received - to be overwritten by derived detail
        implementation.
        """
        pass

    def start(self):
        self.stop_requested = False
        self.thread_active = True
        self.client_thread = threading.Thread(target=self.thread_fct)
        self.client_thread.daemon = True
        self.client_thread.name = "TCPClientThread"
        self.client_thread.start()

    def stop(self):
        logging.info("TcpClient stop requested ...")
        self.stop_requested = True
        self.client_thread.join()
        logging.info("TcpClient stopped.")

    def get_thread_active(self):
        return self.thread_active

    def thread_fct(self):
        while True:
            self.connect()
            if self.connected:
                # connection established, authenticate
                self.send_hello()
                self.event_connected()

                self.sock.settimeout(1)
                while True:
                    # Receive data from the server and shut down
                    received = None
                    try:
                        received = self.sock.recv(1024)
                    except socket.timeout:
                        if self.stop_requested:
                            # break inner loop, on stop requested
                            self.connected = False
                            self.sock.shutdown(socket.SHUT_RDWR)
                            self.sock.close()
                            self.thread_active = False
                            break
                    except (ConnectionAbortedError, ConnectionResetError):
                        self.connected = False
                        logging.info("Client: Connection disconnected")
                        logging.info(self.connected)
                        if sys.platform != "linux":
                            self.sock.shutdown(socket.SHUT_RDWR)
                        self.sock.close()
                        self.thread_active = False
                        break
                    if received is not None:
                        if received == b"":
                            self.connected = False
                            logging.info("Client: Connection disconnected")
                            try:
                                self.sock.shutdown(socket.SHUT_RDWR)
                            except ConnectionResetError:
                                pass
                            self.sock.close()
                            self.thread_active = False
                            break
                        if self.log_received_messages:
                            logging.info("Received msg: '%s'" % received)
                        self.last_message = received
                        self.event_msg_received(received)
            if self.stop_requested or not self.auto_reconnect:
                logging.info(
                    "Client: Stop requested or no-auto-reconnect - stopping ..."
                )
                break
            else:
                logging.info(
                    "Client: Dropped + reconnect enabled - will re-connect ..."
                )
        logging.info("Client: Thread ended.")
        return

    def connect(self):
        """
        Create TCP client socket
        """
        # create socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # connect
        connection_successful = False
        self.connected = False
        retry_count = 0
        while not connection_successful and not self.stop_requested:
            try:
                self.sock.connect((self.host, self.port))
                logging.info("Client: Connected")
                connection_successful = True
                self.connected = True

            except (ConnectionRefusedError, TimeoutError):
                # connect failed
                if not self.retry_connection:
                    raise Exception(
                        "Client connection to server failed and retrying is disabled"
                    )
                else:
                    logging.warning(
                        "Client connection failed - waiting for attempt %d ..."
                        % retry_count
                    )
                    time.sleep(0.5)
                retry_count += 1

    def send_hello(self):
        """
        Authenticate at server with name
        """
        msg = b"HLO name=%s type=%s" % (
            bytes(self.name, "utf-8"),
            bytes(self.type, "utf-8"),
        )
        self.send_msg(msg)

    def send_msg(self, msg: bytes):
        if not self.connected:
            raise Exception("TcpClient: Trying to send message while not connected")
        self.sock.sendall(msg + b"\n")

    def get_last_msg(self):
        return self.last_message

    def set_log_received_messages(self, log_received_messages):
        self.log_received_messages = log_received_messages

    def get_connected(self):
        return self.connected
