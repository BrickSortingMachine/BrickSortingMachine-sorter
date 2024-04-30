import time
import unittest

import test_helpers

import sorter.serial_service.timeout_async


class TimeoutAsyncTest(unittest.TestCase, test_helpers.BaseTest):
    def test_general(self):
        self.setup_logging()

        triggered = False

        def callback_fct():
            nonlocal triggered
            triggered = True

        ta = sorter.serial_service.timeout_async.TimeoutAsync(
            callback_fct=callback_fct, timeout_sec=1.0
        )
        ta.trigger()

        time.sleep(0.5)
        self.assertFalse(triggered)

        time.sleep(2.0)
        self.assertTrue(triggered)

        ta.stop_thread()

        test_helpers.BaseTest.assert_threads_stopped(self)
