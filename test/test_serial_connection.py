import logging
import time
import unittest

import test_helpers

import sorter.serial_service.serical_connection_manager_mock


class SerialConnectionTest(unittest.TestCase, test_helpers.BaseTest):
    def test_connection(self):
        self.setup_logging()
        logging.info("## SerialConnectionTest > test_general")

        (
            SerialConnectionManagerAdapted,
            MySerialConnectionHandler,
        ) = sorter.serial_service.serical_connection_manager_mock.get_manager_mock()

        m = SerialConnectionManagerAdapted(max_iterations=1)

        h = MySerialConnectionHandler()
        m.register_handler("slide-controller", h)

        wait_sec = 10
        for i in range(wait_sec):
            logging.info(f"Main thread still waiting ({i}s / {wait_sec}s) ...")
            time.sleep(1)

        test_helpers.BaseTest.assert_threads_stopped(self)
