import logging
import time
import unittest

import test_helpers

import sorter.network.tcp_client
import sorter.network.tcp_server


class ExampleCommandHandler(sorter.network.tcp_server.RequestHandler):
    def __init__(self, request, client_address, server) -> None:
        super().__init__(request, client_address, server)

    def event_client_disconnected(self):
        logging.info('Client "%s" disconnected' % self.name)

    def process_custom_command(self, message):
        # ABC
        command = message[:3]
        if command == b"ABC":
            logging.info("Received command ABC")

        else:
            raise Exception("Received unsupported command: " "%s" "" % command)

    def send_example(self):
        self.request.sendall(b"DRV\n")


class TestTcpServer(unittest.TestCase, test_helpers.BaseTest):
    def test_minimal(self):
        self.setup_logging()

        # start server
        s = sorter.network.tcp_server.TcpServer("0.0.0.0", 5005, ExampleCommandHandler)
        s.start()
        time.sleep(1)

        c1 = sorter.network.tcp_client.TcpClient(
            "localhost",
            5005,
            name="client01",
            type="client",
            retry_connection=False,
            auto_reconnect=False,
        )
        c1.start()
        time.sleep(0.5)

        # assert client successfully connected
        self.assertEqual(1, len(s.handler_list), "There must be 1 clients connected")

        # assert names registered
        self.assertEqual("client01", s.handler_list[0].get_name())

        c1.stop()
        s.stop()
        time.sleep(0.5)

        test_helpers.BaseTest.assert_threads_stopped(self)

    def test_broadcast(self):
        self.setup_logging()

        # start server
        s = sorter.network.tcp_server.TcpServer("0.0.0.0", 5005, ExampleCommandHandler)
        s.start()

        time.sleep(1)

        c1 = sorter.network.tcp_client.TcpClient(
            "localhost",
            5005,
            name="client01",
            type="client",
            retry_connection=False,
            auto_reconnect=False,
        )
        c1.start()
        time.sleep(0.5)
        c2 = sorter.network.tcp_client.TcpClient(
            "localhost",
            5005,
            name="client02",
            type="client",
            retry_connection=False,
            auto_reconnect=False,
        )
        c2.start()
        time.sleep(0.5)

        # assert all clients successfully connected
        self.assertEqual(2, len(s.handler_list), "There must be 2 clients connected")

        # assert names registered
        self.assertEqual("client01", s.handler_list[0].get_name())
        self.assertEqual("client02", s.handler_list[1].get_name())

        for i in range(5):
            logging.info("Testing broadcast ...")
            s.broadcast(b"msg %d" % i)
            time.sleep(0.2)
            self.assertEqual(c1.get_last_msg(), b"msg %d" % i)
            self.assertEqual(c2.get_last_msg(), b"msg %d" % i)
            time.sleep(0.2)

        c1.stop()
        c2.stop()
        s.stop()

        test_helpers.BaseTest.assert_threads_stopped(self)

    def test_client_stop_while_connecting(self):
        """
        Client connecting w/o server running, stopping it
        Retry connection on
        """
        self.setup_logging()

        c1 = sorter.network.tcp_client.TcpClient(
            "localhost",
            5005,
            name="vehicle01",
            type="vehicle",
            retry_connection=True,
            auto_reconnect=False,
        )
        c1.start()
        logging.info("Connected - waiting to stop ...")
        time.sleep(2)

        # stopping - shall not hang
        c1.stop()
        self.assertTrue(True)

        test_helpers.BaseTest.assert_threads_stopped(self)

    def test_client_loosing_connection_reconnecting(self):
        """
        - Client connecting successfully
        - Server stopping
        - Server starting
        - Client auto-reconnecting
        """
        self.setup_logging()

        # start server
        s = sorter.network.tcp_server.TcpServer("0.0.0.0", 5005, ExampleCommandHandler)
        s.start()
        time.sleep(2)

        # connect client
        c1 = sorter.network.tcp_client.TcpClient(
            "localhost",
            5005,
            name="client1",
            type="none",
            retry_connection=True,
            auto_reconnect=True,
        )
        c1.start()
        time.sleep(2)

        self.assertTrue(c1.get_connected())

        # stop server
        s.stop()
        time.sleep(2)

        self.assertFalse(c1.get_connected())

        # restart server
        s.start()
        logging.info("Server started - waiting for client to re-connect ...")
        time.sleep(2)

        self.assertTrue(c1.get_connected())

        # stop client
        c1.stop()
        time.sleep(0.5)

        # stop server
        s.stop()

        test_helpers.BaseTest.assert_threads_stopped(self)

    def test_2_clients_same_name(self):
        """
        - 1st Client connecting
        - 2nd Client connecting
           ->
        1st client shall be disconnected
        """
        self.setup_logging()

        # start server
        s = sorter.network.tcp_server.TcpServer("0.0.0.0", 5005, ExampleCommandHandler)
        s.start()
        time.sleep(0.5)

        # 1st client
        c1 = sorter.network.tcp_client.TcpClient(
            "localhost",
            5005,
            name="client1",
            type="none",
            retry_connection=False,
            auto_reconnect=False,
        )
        c1.start()
        time.sleep(0.5)

        self.assertTrue(c1.get_connected())

        # server request handler for client 1 running
        self.assertEqual(1, len(s.get_handler_list()))
        request_handler = s.get_handler_list()[0]
        self.assertFalse(request_handler.get_stopped())

        # 2nd client
        c2 = sorter.network.tcp_client.TcpClient(
            "localhost",
            5005,
            name="client1",
            type="none",
            retry_connection=False,
            auto_reconnect=False,
        )
        c2.start()
        time.sleep(2)

        self.assertTrue(c2.get_connected())

        # must have =1 handler - other shall be auto-disconnected
        handler_list = s.get_handler_name_list()
        self.assertEqual(1, len(handler_list))

        # server request handler for client 1 shall be stopped now
        self.assertTrue(request_handler.get_stopped())

        # stop 2nd client
        c2.stop()
        time.sleep(0.5)

        # stop 1st client
        c1.stop()
        time.sleep(0.5)

        # stop server
        s.stop()

        test_helpers.BaseTest.assert_threads_stopped(self)
