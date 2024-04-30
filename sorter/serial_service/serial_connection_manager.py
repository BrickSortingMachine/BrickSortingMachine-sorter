import glob
import logging
import threading
import time

import serial


class SerialConnectionManager:
    def __init__(self, max_iterations=None):
        self.connection_list = []
        self.handler_list = []

        self.max_iterations = max_iterations

        # wait for connections thread
        self.thread = threading.Thread(target=self.thread_fct)
        self.thread.daemon = True  # have no explicit stopping mechanism
        self.thread.name = "SerialManager wait for new connections thread"
        self.thread.start()

    def thread_fct(self):
        # wait for new serial connection
        self.handle_new_connections()

    def handle_new_connections(self):
        """
        Wait for new devices, start new connection
        """
        iteration_count = 0
        while True:
            # get unconnected
            path_list = self.get_not_connected_devices()
            if len(path_list) == 0:
                # logging.info('No new devices - waiting ...')
                pass
            else:
                logging.info(f"Found new devices {path_list}")

            # connect
            for path in path_list:
                connection = self.connect_serial(path)

                # HLO
                id = self.identify_connection(connection)

                # connect handler
                handler = self.get_handler_by_id(id)
                if handler is None:
                    raise Exception(f'Connection "{id}" has no registered handler')

                # thread
                thread = threading.Thread(
                    target=lambda: self.thread_fct_connection(connection, handler)
                )
                thread.daemon = True  # have no explicit stopping mechanism
                thread.name = "SerialConMan Device connection Thread"
                thread.start()

                self.connection_list.append(
                    {
                        "id": id,
                        "path": path,
                        "connection": connection,
                        "thread": thread,
                        "handler": handler,
                    }
                )

            iteration_count += 1
            if (
                self.max_iterations is not None
                and iteration_count > self.max_iterations
            ):
                logging.info("breaking")
                break

            time.sleep(5)

    def thread_fct_connection(self, connection, handler):
        """
        Thread for each connection
        """
        logging.info("SerConMan: Thread started ...")

        handler.base_event_connected(connection)

        while True:
            try:
                data = b""
                while len(data) == 0:
                    data = connection.readline()
                handler.base_event_data_received(connection, data)
            except (serial.SerialException, serial.serialutil.SerialException):
                logging.info("SerConMan: Serial Connection dropped.")
                break

        handler.base_event_disconnected(connection)

        # remove from connection list
        len_before = len(self.connection_list)
        self.connection_list = list(
            filter(lambda con: con["connection"] != connection, self.connection_list)
        )
        len_after = len(self.connection_list)
        assert len_after == len_before - 1

        logging.info("SerConMan: Thread ended.")

    def register_handler(self, id, handler):
        self.handler_list.append(
            {
                "id": id,
                "handler": handler,
            }
        )

    def get_device_list(self):
        return glob.glob("/dev/ttyUSB*")

    def get_not_connected_devices(self):
        path_list = self.get_device_list()

        connected_path_list = list(
            map(lambda connection: connection["path"], self.connection_list)
        )

        path_list = list(
            filter(lambda path: path not in connected_path_list, path_list)
        )

        return path_list

    def connect_serial(self, path):
        return serial.Serial(path, baudrate=9600, timeout=1)

    def identify_connection(self, connection):
        # arduino usually not answers on first try
        max_retries = 3
        for i in range(max_retries):
            connection.write(b"HLO\n")
            time.sleep(0.5)
            data = connection.readline().decode("UTF-8").strip()
            if data.startswith("HLO "):
                identifier = data.split(" ")[1]
                logging.info(f'Serial identified as "{identifier}"')
                break
            if i >= max_retries - 1:
                raise Exception(f"Max connection retries {max_retries} reached")
        return identifier

    def get_handler_by_id(self, id):
        filtered_list = list(
            filter(lambda handler: handler["id"] == id, self.handler_list)
        )
        if len(filtered_list) > 1:
            raise Exception(f"Multiple handler with id {id}")
        if len(filtered_list) == 0:
            return None
        return filtered_list[0]["handler"]
