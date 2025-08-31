import logging
import socket
import socketserver
import threading


class TcpServer:
    """
    Basics TcpServer with multiple connection handling (w/o control server or city specific aspects)
    """

    def __init__(self, host, port, server_command_handler_class):
        self.host = host
        self.port = port
        self.server_command_handler_class = server_command_handler_class
        self.server_socket = None
        self.server_thread = None
        self.handler_list = []
        self.server_ready = threading.Event()

    def start(self):
        socketserver.ThreadingMixIn.daemon_threads = True
        socketserver.ThreadingTCPServer.allow_reuse_address = (
            True  # Fix: OSError: [Errno 98] Address already in use
        )
        socketserver.TCPServer.allow_reuse_address = True
        self.server_thread = threading.Thread(target=self.server_fct)
        self.server_thread.daemon = True
        self.server_thread.start()
        self.server_thread.name = "TCPServingThread"
        self.server_ready.wait()  # Wait until the server is ready

    def stop(self):
        logging.info("Server: Stop requested")
        for handler in self.handler_list:
            handler.request_stop()
        if self.server_socket:
            self.server_socket.shutdown()
            self.server_socket.server_close()
        if self.server_thread:
            self.server_thread.join()

    def broadcast(self, message):
        for handler in self.handler_list:
            try:
                handler.sendall(message)
            except ConnectionResetError:
                logging.error("Client connection was not available anymore")

    def client_connected(self, handler):
        logging.info("Server: Client connected")
        self.handler_list.append(handler)

    def client_disconnected(self, handler):
        logging.info("Server: Client disconnected")
        connection_count_before = len(self.handler_list)
        self.handler_list = list(filter(lambda h: h != handler, self.handler_list))
        connection_count_after = len(self.handler_list)
        assert connection_count_before - 1 == connection_count_after

    def get_handler_name_list(self):
        return list(map(lambda handler: handler.get_name(), self.handler_list))

    def get_handler_by_name(self, name):
        matching_handler_list = list(
            filter(lambda handler: handler.get_name() == name, self.handler_list)
        )
        if len(matching_handler_list) > 1:
            logging.error("List of matching handlers' hosts:")
            for index, h in enumerate(matching_handler_list):
                logging.error(" %d:  %s" % (index, h.client_address[0]))
            raise Exception(
                "Two handlers exist with name '%s' - possibly multiple connect or old connection."
                % name
            )

        if len(matching_handler_list) == 0:
            return None
        else:
            return matching_handler_list[0]

    def remove_client(self, handler):
        handler.request_stop()
        connection_count_before = len(self.handler_list)
        self.handler_list = list(filter(lambda h: h != handler, self.handler_list))
        connection_count_after = len(self.handler_list)
        assert connection_count_before - 1 == connection_count_after

    def server_fct(self):
        # create server inside deamon thread so that deamon status is inherited by connection threads
        try:
            self.server_socket = socketserver.ThreadingTCPServer(
                (self.host, self.port), self.server_command_handler_class
            )
            # Not clean but only way found to communicate self (TcpServer) to the RequestHandlers
            self.server_socket.tcp_server = self
            logging.info("Server: Thread running")
            self.server_ready.set()
            self.server_socket.serve_forever(poll_interval=1)
        except Exception as e:
            logging.error(f"Server: Thread ended with exception: {e}")
            self.server_ready.set()  # Also signal if there's an error
        finally:
            logging.info("Server: Thread stopped")

    def get_handler_list(self):
        return self.handler_list


class RequestHandler(socketserver.BaseRequestHandler):
    def __init__(self, request, client_address, server) -> None:
        # assignments needed before super().__init__() since needed in there
        self.name = None
        self.request = request
        self.tcp_server = server.tcp_server

        super().__init__(request, client_address, server)

    def request_stop(self):
        """
        Asking for handler to stop (check get_stopped() to check if stopped successfully)
        """
        self.stop_requested = True

    def sendall(self, msg):
        logging.info("Sending: %s" % msg)
        self.request.sendall(msg)

    def get_name(self):
        return self.name

    def handle(self):
        threading.current_thread().name = "TcpServer RequestHandler"

        self.tcp_server.client_connected(self)
        self.event_client_connected()
        self.stop_requested = False
        self.stopped = False
        logging.info(f"Handler for {self.name} started.")

        while not self.stop_requested:
            logging.debug(f"Handler for {self.name} loop, stop_requested={self.stop_requested}")
            try:
                # timeout receive frequently to detect server to be closed
                self.request.settimeout(1)
                self.data = self.request.recv(1024)
                if not self.data:
                    self.tcp_server.client_disconnected(self)
                    self.event_client_disconnected()
                    break
            except socket.timeout:
                continue  # Just continue the loop on timeout
            except ConnectionResetError:
                self.tcp_server.client_disconnected(self)
                self.event_client_disconnected()
                break
            except Exception as e:
                logging.error(f"Unexpected error in RequestHandler: {e}")
                self.tcp_server.client_disconnected(self)
                self.event_client_disconnected()
                break

            # check message is complete, i.e. last byte is newline
            if not self.data.endswith(b"\n"):
                logging.warning("Incomplete message received, discarding.")
                continue
            self.data = self.data.strip()

            # break multiple messages received together
            msg_list = self.data.split(b"\n")

            for msg in msg_list:
                # HLO
                if len(msg) >= 3 and msg[:3] == b"HLO":
                    message_parts = str(msg, "utf-8").split(" ")
                    # not directly assign name otherwise found as duplicate name below
                    name = message_parts[1].split("=")[1]

                    # already connected handlers with same name
                    same_name_handler = self.tcp_server.get_handler_by_name(name)
                    if same_name_handler is not None:
                        logging.warning(
                            "Previous connection with same name exists - disconnecting the old one"
                        )
                        self.tcp_server.remove_client(same_name_handler)

                    self.name = name
                    logging.info('Server: Client identified as "%s"' % self.name)
                    threading.current_thread().name = (
                        "TcpServer RequestHandler (id: " + self.name + ")"
                    )
                    self.event_client_hello()

                else:
                    # forwards unknown commands to specific implementation
                    if msg != b"":
                        self.process_custom_command(msg)

        self.stopped = True
        logging.info("Request handler stopped.")

    def get_stopped(self):
        return self.stopped

    def event_client_connected(self):
        """
        To be re-implemented in specialization class if needed
        """
        pass

    def event_client_hello(self):
        """
        To be re-implemented in specialization class if needed
        """
        pass

    def event_client_disconnected(self):
        """
        To be re-implemented in specialization class if needed
        """
        pass
