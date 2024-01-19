import logging
import sys
import threading
import traceback


class BaseTest:
    def __init__(self) -> None:
        logging.info("init called")

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
        logging.info("ok")

    @staticmethod
    def setup_logging():
        """
        Configures the logging module uniformly over the test cases
        """
        logging.basicConfig(
            format="%(levelname)s %(asctime)s %(filename)s:%(lineno)d %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            level=logging.DEBUG,
        )

        # switch off matplotlib debug messages for font manager
        logging.getLogger("matplotlib.font_manager").disabled = True

    @staticmethod
    def create_config():
        """
        Create a config equivalent which is replace the GPReportingServerConfig.json which is used by the production server
        :return: dict containing config info
        """
        return {
            "enable_worker": False,
            "hostname": "localhost",
            "port": "5234",
            #    'data_folder_path': os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))
        }
