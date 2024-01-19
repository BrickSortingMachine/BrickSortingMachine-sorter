import logging
import time
import unittest

import test_helpers

import sorter.network.tcp_server
import sorter.serial_service.serial_service
import sorter.serial_service.serical_connection_manager_mock
import sorter.serial_service.slide_serial_connection_handler


class SerialServiceTest(unittest.TestCase, test_helpers.BaseTest):
    def test_general(self):
        self.setup_logging()
        logging.info("## SerialServiceTest > test_general")

        # server
        s = sorter.network.tcp_server.TcpServer(
            "0.0.0.0", 5005, sorter.network.tcp_server.RequestHandler
        )
        s.start()
        time.sleep(0.5)

        # patch connection
        def my_create_connection_manager(self, max_iterations):
            (
                SerialConnectionManagerAdapted,
                _,
            ) = sorter.serial_service.serical_connection_manager_mock.get_manager_mock()
            return SerialConnectionManagerAdapted(max_iterations)

        sorter.serial_service.serial_service.SerialService.create_connection_manager = (
            my_create_connection_manager
        )

        # serial service
        ss = sorter.serial_service.serial_service.SerialService(
            host="localhost", disable_network=False, max_iterations=1
        )
        time.sleep(1)

        # classification result
        msg = "CLR 0 plate1x 1 100 1.218174 W3siY2xhc3MiOiAicGxhdGUxeCIsICJwcm9iYWJpbGl0eSI6IDF9LCB7ImNsYXNzIjogImJyaWNrMXgiLCAicHJvYmFiaWxpdHkiOiAwfSwgeyJjbGFzcyI6ICJicmljazJ4IiwgInByb2JhYmlsaXR5IjogMH1d W3siY2xhc3MiOiAicGxhdGUxeCIsICJwcm9iYWJpbGl0eSI6IDF9LCB7ImNsYXNzIjogImJyaWNrMXgiLCAicHJvYmFiaWxpdHkiOiAwfSwgeyJjbGFzcyI6ICJicmljazJ4IiwgInByb2JhYmlsaXR5IjogMH1d"
        s.broadcast(bytes(msg, "utf-8"))

        # wait long so SerialConnectionManager stop waiting for new connections
        time.sleep(6)

        # stop serial / client
        ss.stop()

        # stop server
        s.stop()

        test_helpers.BaseTest.assert_threads_stopped(self)

    def test_slide_return_to_center(self):
        self.setup_logging()
        logging.info("## SerialServiceTest > test_slide_return_to_center")

        connection_write_count = 0

        class DummyConnection:
            def write(self, _):
                nonlocal connection_write_count
                connection_write_count += 1

        sh = (
            sorter.serial_service.slide_serial_connection_handler.SlideSerialConnectionHandler()
        )
        sh.connection = DummyConnection()
        sh.event_receive_classification_result(
            "brick2x", pred_low_list=[], pred_high_list=[]
        )
        time.sleep(2.5)

        # turned towards box
        self.assertEqual(1, connection_write_count)
        time.sleep(2)

        # write triggered 2nd time for return
        self.assertEqual(2, connection_write_count)

        sh.stop()

        test_helpers.BaseTest.assert_threads_stopped(self)
