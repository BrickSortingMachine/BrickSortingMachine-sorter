import time
import unittest

import test_helpers

import sorter.controller.hour_meter


class HourMeterTest(unittest.TestCase, test_helpers.BaseTest):
    def test_general(self):
        self.setup_logging()

        hm = sorter.controller.hour_meter.HourMeter()
        hm.start()
        time.sleep(1)
        hm.stop()

        test_helpers.BaseTest.assert_threads_stopped(self)
