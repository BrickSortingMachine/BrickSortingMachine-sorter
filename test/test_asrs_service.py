import sys
from unittest import mock

sys.modules["playsound"] = mock.MagicMock()

import time

import test_helpers

import sorter.asrs_service.asrs_service
import sorter.network.tcp_server


class ASRSServiceTest(test_helpers.BaseTest):
    def test_via_network(self):
        """
        General
        """
        self.setup_logging()

        # dummy server
        s = sorter.network.tcp_server.TcpServer(
            "0.0.0.0", 5005, sorter.network.tcp_server.RequestHandler
        )
        s.start()
        time.sleep(1)

        cs = sorter.asrs_service.asrs_service.ASRSService(
            host="127.0.0.1",
            disable_network=False,
            disable_device=True,
        )
        time.sleep(1)

        s.broadcast(b"NTF part_scanned")
        time.sleep(2)

        s.broadcast(b"NTF double_part_scanned")
        time.sleep(2)

        # stop network
        cs.stop()
        s.stop()

    def test_part_scanned(self):
        self.setup_logging()

        cs = sorter.notification_service.notification_service.NotificationService(
            host=None, disable_network=True, theme="kids", disable_pushover=True
        )
        cs.notify("part_scanned", "No Msg")

        test_helpers.BaseTest.assert_threads_stopped(self)

    def test_scanner_inhibition_ended(self):
        self.setup_logging()

        cs = sorter.notification_service.notification_service.NotificationService(
            host=None, disable_network=True, theme="kids", disable_pushover=True
        )
        cs.notify("scanner_inhibition_ended", "No Msg")

        test_helpers.BaseTest.assert_threads_stopped(self)

    def test_classification_result(self):
        self.setup_logging()

        cs = sorter.notification_service.notification_service.NotificationService(
            host=None, disable_network=True, theme="robot_german", disable_pushover=True
        )
        cs.notify("classification_result", "plate1x")
        cs.notify("classification_result", "plate2x")
        cs.notify("classification_result", "tile")
        cs.notify("classification_result", "brick2x")
        cs.notify("classification_result", "skip")

        test_helpers.BaseTest.assert_threads_stopped(self)

    def test_double_part_scanned(self):
        self.setup_logging()

        cs = sorter.notification_service.notification_service.NotificationService(
            host=None, disable_network=True, theme="robot_german", disable_pushover=True
        )
        cs.notify("double_part_scanned", "")

        test_helpers.BaseTest.assert_threads_stopped(self)

    def test_timeout_max_non_busy(self):
        self.setup_logging()

        cs = sorter.notification_service.notification_service.NotificationService(
            host=None, disable_network=True, theme="kids", disable_pushover=True
        )
        cs.notify("timeout_max_non_busy", "30")

        test_helpers.BaseTest.assert_threads_stopped(self)

    def test_pushover(self):
        self.setup_logging()

        cs = sorter.notification_service.notification_service.NotificationService(
            host=None, disable_network=True, theme="kids", disable_pushover=True
        )
        cs.pushover("hello world thx!!")

        test_helpers.BaseTest.assert_threads_stopped(self)
