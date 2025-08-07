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
            verbose=True,
        )
        time.sleep(1)

        # classification result
        msg = "CLR 0 plate1x 1 100 1.218174 W3siY2xhc3MiOiAicGxhdGUxeCIsICJwcm9iYWJpbGl0eSI6IDF9LCB7ImNsYXNzIjogImJyaWNrMXgiLCAicHJvYmFiaWxpdHkiOiAwfSwgeyJjbGFzcyI6ICJicmljazJ4IiwgInByb2JhYmlsaXR5IjogMH1d W3siY2xhc3MiOiAicGxhdGUxeCIsICJwcm9iYWJpbGl0eSI6IDF9LCB7ImNsYXNzIjogImJyaWNrMXgiLCAicHJvYmFiaWxpdHkiOiAwfSwgeyJjbGFzcyI6ICJicmljazJ4IiwgInByb2JhYmlsaXR5IjogMH1d"
        s.broadcast(bytes(msg, "utf-8"))

        # stop network
        asrs.stop()
        s.stop()
