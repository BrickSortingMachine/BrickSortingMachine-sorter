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

        asrs = sorter.asrs_service.asrs_service.ASRSService(
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
        asrs.stop()
        s.stop()

    def test_part_scanned(self):
        self.setup_logging()

        # asrs = sorter.asrs_service.asrs_service.ASRSService(
        #     host=None, disable_network=True, theme="kids", disable_pushover=True
        # )
