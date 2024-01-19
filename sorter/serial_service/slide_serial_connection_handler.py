import logging

import sorter.serial_service.serial_connection_handler
import sorter.serial_service.timeout_async

rot_dict = {
    0: 90,
    1: 72,
    2: 56,
    3: 40,
    4: 24,
    5: 9,
    7: 173,
    8: 157,
    9: 141,
    10: 126,
    11: 110,
}
el = 0

class_pose_map = {
    "slope1x": {"rot": rot_dict[7], "el": el},
    "slope": {"rot": rot_dict[7], "el": el},
    "car": {"rot": rot_dict[8], "el": el},
    "brick_modified": {"rot": rot_dict[9], "el": el},
    "brick1x": {"rot": rot_dict[10], "el": el},
    "brick2x": {"rot": rot_dict[11], "el": el},
    "skip": {"rot": rot_dict[0], "el": el},
    "plate1x": {"rot": rot_dict[1], "el": el},
    "plate2x": {"rot": rot_dict[2], "el": el},
    "plate_modified": {"rot": rot_dict[3], "el": el},
    "tile": {"rot": rot_dict[4], "el": el},
    "small": {"rot": rot_dict[5], "el": el},
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
