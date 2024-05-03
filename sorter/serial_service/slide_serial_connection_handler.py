import logging

import sorter.serial_service.serial_connection_handler
import sorter.serial_service.timeout_async

r = {
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
e = {
    "low": 100,
    "high": 170,
}

class_pose_map = {
    "skip": {"rot": r[0], "el": e["low"]},
    "multiple_parts": {"rot": r[0], "el": e["low"]},
    "bar": {"rot": r[1], "el": e["low"]},
    "brick1x": {"rot": r[2], "el": e["low"]},
    "brick2x": {"rot": r[3], "el": e["low"]},
    "brick_modified": {"rot": r[4], "el": e["low"]},
    "car": {"rot": r[5], "el": e["low"]},
    "hinge": {"rot": r[6], "el": e["low"]},
    "human": {"rot": r[7], "el": e["low"]},
    "plane": {"rot": r[8], "el": e["low"]},
    "plate": {"rot": r[9], "el": e["low"]},
    "plate1x": {"rot": r[10], "el": e["low"]},
    "plate2x": {"rot": r[0], "el": e["high"]},
    "plate_modified": {"rot": r[1], "el": e["high"]},
    "plate_shaped": {"rot": r[2], "el": e["high"]},
    "round": {"rot": r[3], "el": e["high"]},
    "round_slope": {"rot": r[4], "el": e["high"]},
    "slope": {"rot": r[5], "el": e["high"]},
    "slope1x": {"rot": r[6], "el": e["high"]},
    "small": {"rot": r[7], "el": e["high"]},
    "tile": {"rot": r[8], "el": e["high"]},
    "window": {"rot": r[9], "el": e["high"]},
}


class SlideSerialConnectionHandler(
    sorter.serial_service.serial_connection_handler.SerialConnectionHandlerBase
):
    def __init__(self) -> None:
        super().__init__()

        # timeout to return to center position
        self.return_center_timeout = sorter.serial_service.timeout_async.TimeoutAsync(
            callback_fct=self.return_center, timeout_sec=4.0
        )

        self.callback_motion_completed = None

    def stop(self):
        self.return_center_timeout.stop_thread()

    def event_connected(self, connection):
        pass

    def event_disconnected(self, connection):
        pass

    def event_data_received(self, connection, data: bytes):
        if data.strip() == b"GOT motion completed":
            if self.callback_motion_completed is not None:
                self.callback_motion_completed()

    def event_receive_classification_result(
        self, predicted_class, pred_low_list, pred_high_list
    ):
        logging.info(pred_low_list)
        logging.info(pred_high_list)

        # skip bin
        if predicted_class == "skip" or predicted_class.startswith("inc_"):
            predicted_class = "skip"

        # unknown class
        if predicted_class not in class_pose_map:
            logging.warning(f"No bin specified for class {predicted_class} - skip bin.")
            predicted_class = "skip"

        # rotate to bin
        pose = class_pose_map[predicted_class]
        self.move_slide(pose["rot"], pose["el"])

        # timer to return to center
        self.return_center_timeout.trigger()

    def return_center(self):
        pose = class_pose_map["skip"]
        self.move_slide(pose["rot"], pose["el"])

    def move_slide(self, rot: int, el: int):
        logging.info(f"Moving slide to rot={rot} el={el} ...")

        assert 0 <= rot <= 180
        assert 0 <= el <= 180
        msg = bytes(f"GOT {el} {rot}\n", "utf-8")
        logging.info(f"msg={msg}")
        self.get_connection().write(msg)

    def set_callback_motion_completed(self, callback):
        self.callback_motion_completed = callback
