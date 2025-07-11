import logging
import sys
import threading
import traceback
import unittest


class BaseTest(unittest.TestCase):
    def assert_threads_stopped(self):
        logging.info("Checking all threads stopped ...")
        for thread in threading.enumerate():
            if thread.name != "MainThread":
                # print callstack of non-stopped thread
                stack = traceback.extract_stack(sys._current_frames()[thread.ident])
                print("Stack for thread {}:".format(thread.ident))
                for frame in stack:
                    print(frame)

                # warn about non-stopped thread
                raise Exception(
                    f"Thread with name {thread.name} still running at end of test (will cause subsequent hidden failures since unittest run in same process)."
                )
        print("All threads stopped ✔")
        logging.info("All threads stopped ✔")

    def setup_logging(self):
        """
        Configures the logging module uniformly over the test cases
        """
        logging.basicConfig(
            format="%(name)s %(levelname)s %(asctime)s %(filename)s:%(lineno)d %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            level=logging.DEBUG,
        )

        # switch off matplotlib debug messages for font manager
        logging.getLogger("matplotlib.font_manager").disabled = True

    def setUp(self):
        self.setup_logging()

    def tearDown(self):
        self.assert_threads_stopped()
