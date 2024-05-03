import logging
import os
import sys
import time
import traceback

# add robolab folder to python path
p = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(p)

import sorter.argument_parser
import sorter.serial_connection.manager
import sorter.serial_service.slide_serial_connection_handler

logging.basicConfig(
    format="%(levelname)s %(asctime)s %(filename)s:%(lineno)d %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.DEBUG,
)

parser = sorter.argument_parser.ArgumentParser(description="Manual Commands")
parser.add_argument("--test_mode", action="store_true", required=False)
args = parser.parse_args()


class DummyConnection:
    def __init__(self, slide) -> None:
        self.slide = slide

    def write(self, _):
        logging.info("Waiting ...")
        time.sleep(1)
        self.slide.event_data_received(self, b"GOT motion completed")


# slide serial connection
slide = (
    sorter.serial_service.slide_serial_connection_handler.SlideSerialConnectionHandler()
)
if not args.test_mode:
    manager = sorter.serial_connection.manager.SerialConnectionManager()
    manager.register_handler("slide-controller", slide)
else:
    # mock connection manager (not have physical serial connection)
    slide.connection = DummyConnection(slide)

motion_completed = True


def callback_motion_completed():
    """
    Callback motion complete
    """
    global motion_completed
    logging.info("Motion completed")
    motion_completed = True


def move_and_wait(new_position, new_elevation):
    """
    Blocking Motion Request
    """
    global motion_completed
    motion_completed = False
    slide.move_slide(new_position, new_elevation)
    while not motion_completed:
        time.sleep(0.5)
    logging.info("done")


# install callback
slide.set_callback_motion_completed(callback_motion_completed)

# wait serial connected
logging.info("Connecting ...")
while not slide.is_connected():
    time.sleep(0.5)
logging.info("Connected.")

rot_dict = {
    10: 168,
    9: 152,
    8: 136,
    7: 123,
    6: 107,
    0: 90,
    1: 74,
    2: 58,
    3: 46,
    4: 32,
    5: 16,
}
el_dict = {
    "low": 100,
    "high": 170,
}

try:
    # move through pose list
    pose_list = [
        (0, False),
        (4, True),
        (1, False),
        (2, True),
        (8, True),
        (6, True),
        (2, False),
        (9, True),
        (10, True),
        (3, False),
        (5, True),
        (10, False),
        (0, True),
        (7, True),
        (3, True),
        (4, False),
        (5, False),
        (9, False),
        (1, True),
        (6, False),
        (7, False),
        (8, False),
    ]
    while True:
        for pose_index, pose in enumerate(pose_list):
            rot_index, low = pose
            rot = rot_dict[rot_index]
            el = el_dict["low" if low else "high"]
            logging.info(" ")
            logging.info(f"Requesting pose {pose_index} (rot={rot}, el={el}) ...")
            move_and_wait(rot, el)
except KeyboardInterrupt:
    trace = traceback.format_exc()
    logging.exception(trace)

# home
logging.info(" ")
logging.info("Sequence completed - homing ...")
move_and_wait(90, 90)

logging.info("Stopped.")
