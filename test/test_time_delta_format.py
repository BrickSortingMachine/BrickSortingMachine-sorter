import logging
import unittest

import test_helpers

import sorter.util.time_delta_format


class TimeDeltaFormatTest(unittest.TestCase, test_helpers.BaseTest):
    def test_general(self):
        self.setup_logging()

        t = 4 * 60 * 60 + 30 * 60 + 2
        s = sorter.util.time_delta_format.time_delta_format(t)
        logging.info(f'"{s}"')
