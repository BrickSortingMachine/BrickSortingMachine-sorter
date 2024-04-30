import datetime
import json
import logging
import os
import pathlib
import sys
from dataclasses import dataclass
from enum import Enum

import cv2

import sorter.classification_service.classification_service
import sorter.classification_service.config
import sorter.classification_service.crop_image
import sorter.network.tcp_client
import sorter.notification_service.notification_client
import sorter.util.config_handler
import sorter.util.time_delta_format
import sorter.vision_service.camera_capture
import sorter.vision_service.draw_bg_box
import sorter.vision_service.object_detector


@dataclass
class CollectLoopDataItem:
    object_id: int = None
    filepath: str = None
    predicted_class: str = None
    probability: float = None
    uniqueness: float = None
    average_process_time_sec: float = None
    dt: datetime.datetime = None


class CollectionMode(Enum):
    TRAINING = 0
    TESTING = 1
    TRASH = 2
    INCONSISTENT = 3
    KEEP_INCORRECT = 4


class VSTcpClient(sorter.network.tcp_client.TcpClient):
    def __init__(
        self, host, port, name, type, retry_connection, auto_reconnect, vision_service
    ):
        super().__init__(host, port, name, type, retry_connection, auto_reconnect)
        self.vision_service: VisionService = vision_service

    def event_msg_received(self, msg):
        part_list = str(msg, "utf-8").split(" ")

        try:
            # classification result
            if part_list[0] == "CLR":
                object_id = int(part_list[1])
                predicted_class = part_list[2]
                probability = float(part_list[3])
                uniqueness = float(part_list[4])
                average_process_time_sec = float(part_list[5])
                pred_low_serialized = part_list[6]
                pred_high_serialized = part_list[7]
                pred_low_list = sorter.classification_service.classification_service.ClassificationService.deserialize(
                    pred_low_serialized
                )
                pred_high_list = sorter.classification_service.classification_service.ClassificationService.deserialize(
                    pred_high_serialized
                )
                logging.info(
                    f"Received classification result - id: {object_id} pc: {predicted_class}"
                    " prob: {probability*100:.0f}% uniqueness: {uniqueness:.0f}"
                )
                self.vision_service.receive_classification_result(
                    object_id,
                    predicted_class,
                    probability,
                    uniqueness,
                    average_process_time_sec,
                    pred_low_list,
                    pred_high_list,
                )

            # hour meter
            elif part_list[0] == "HMV":
                hour_meter_sec = float(part_list[1])
                self.vision_service.receive_hour_meter_value(hour_meter_sec)
        except ValueError:
            logging.error(
                "Decoding network message error - could be malformed/entangled messages"
            )


class VisionService:
    def __init__(
        self,
        recording,
        object_class: str,
        no_write,
        host,
        disable_network,
        enable_visualization_fullscreen,
    ):
        self.max_sec_since_last_busy = 60
        self.time_since_last_busy_msg_interval_sec = 120

        self.object_class = object_class
        self.disable_network = disable_network
        self.no_write = no_write
        self.count_written = 0
        self.last_received_hour_meter_sec = None

        self.soft_estop_enabled = True
        self.soft_estop_last_sent_frame_index = -1  # estop is resent periodically
        self.soft_estop_enabled_last_frame = None  # estop changed detection

        if not self.disable_network:
            self.tcp_client = VSTcpClient(
                host,
                5005,
                "VisionService",
                "VisionService",
                retry_connection=True,
                auto_reconnect=True,
                vision_service=self,
            )
            self.tcp_client.start()
        else:
            self.tcp_client = None

        self.notification_client = (
            sorter.notification_service.notification_client.NotificationClient(
                self.tcp_client
            )
        )

        # fisheye
        self.camera_fisheye = sorter.vision_service.camera_capture.CameraCapture(
            camera_name="fisheye", recording=recording
        )
        self.od = sorter.vision_service.object_detector.ObjectDetector(
            self.notification_client
        )

        c = sorter.classification_service.config
        self.incoming_data_known_class_train_folder_path = (
            c.incoming_data_known_class_train_dir_path
        )
        self.incoming_data_known_class_test_folder_path = (
            c.incoming_data_known_class_test_dir_path
        )
        self.trash_folder_path = c.trash_dir_path
        self.inconsistent_folder_path = c.inconsistent_dir_path

        # time since belt busy
        self.dt_belt_last_busy = datetime.datetime.now()
        self.dt_belt_busy_time_msg_sent = (
            None  # dt, when time since last belt busy signal was sent over network
        )

        # data for collect loop
        self.min_fps = 20
        self.collect_loop_frame_index = 0
        self.collect_loop_data_list = []
        self.collect_loop_last_frame_inhibited = False
        self.collect_loop_last_frame_belt_busy = False
        self.collect_loop_dt_last_frame = datetime.datetime.now()
        self.collect_loop_smooth_fps = 0
        self.collect_loop_average_part_per_sec = 0
        self.collect_loop_low_fps_frame_count = 0

        # default test because less danger for class mixups
        self.collection_mode = CollectionMode.TRASH

        self.enable_visualization = True
        self.enable_visualization_fullscreen = enable_visualization_fullscreen
        self.enable_viz_mask = False

        # visu classification
        self.detected_crop_low = None
        self.detected_crop_high = None
        self.last_pred_low_list = None
        self.last_pred_high_list = None

    def stop(self):
        if not self.disable_network:
            self.tcp_client.stop()

    def collect(self):
        self.loop_setup()
        while True:
            b = self.loop_step()
            if b:
                break
        return self.collect_loop_data_list

    def loop_setup(self):
        self.collect_loop_frame_index = 0
        self.collect_loop_data_list = []
        self.collect_loop_last_frame_inhibited = False
        self.collect_loop_last_frame_belt_busy = False

    def loop_step(self):
        frame = self.camera_fisheye.capture()
        if frame is None:
            logging.info("Sequence ended.")
            return True
        trigger, frame_viz, component_list, belt_busy = self.od.process_frame(
            self.collect_loop_frame_index,
            frame,
            self.enable_visualization,
            self.enable_viz_mask,
        )

        # NOTICE: This is latency critical - do not put beeps in which delay the reaction
        # belt busy
        # not-busy -> busy
        msg = None
        if not self.collect_loop_last_frame_belt_busy and belt_busy:
            logging.info("Belt status: Busy detected")
            msg = b"BST busy %d" % self.collect_loop_frame_index

            # enable logitech capture
            # self.camera_logitech.capture_multithreaded.set_enable_capture(True)
        # busy -> not-busy
        if self.collect_loop_last_frame_belt_busy and not belt_busy:
            logging.info("Belt status: Not busy anymore")
            msg = b"BST not-busy %d" % self.collect_loop_frame_index

            # disable logitech capture
            # self.camera_logitech.capture_multithreaded.set_enable_capture(False)
        if msg is not None:
            if not self.disable_network and self.tcp_client.get_connected():
                self.tcp_client.send_msg(msg)
        self.collect_loop_last_frame_belt_busy = belt_busy
        sec_since_last_busy = self.handle_timeout_max_non_busy(belt_busy)

        # notify not inhibitted
        inhibitted = self.od.currently_inhibited(self.collect_loop_frame_index)
        if self.collect_loop_last_frame_inhibited and not inhibitted:
            self.notification_client.notify_scanner_inhibition_ended()
        self.collect_loop_last_frame_inhibited = inhibitted

        # detection
        if trigger:
            logging.info("Triggered ...")
            self.notification_client.notify_part_scanned()

            # write image
            object_id = self.count_written

            # image folder
            if self.collection_mode == CollectionMode.TRAINING:
                folder_path = self.incoming_data_known_class_train_folder_path
            elif self.collection_mode == CollectionMode.TESTING:
                folder_path = self.incoming_data_known_class_test_folder_path
            elif self.collection_mode == CollectionMode.TRASH:
                folder_path = self.trash_folder_path
            elif self.collection_mode == CollectionMode.INCONSISTENT:
                folder_path = self.inconsistent_folder_path
            elif self.collection_mode == CollectionMode.KEEP_INCORRECT:
                folder_path = self.incoming_data_known_class_train_folder_path
            else:
                raise Exception("Unknown collection mode")

            fp_wo_suffix = folder_path / (
                "train_" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            )
            if not self.no_write and not self.soft_estop_enabled:
                if not folder_path.exists():
                    folder_path.mkdir()
                assert folder_path.is_dir()

                cv2.imwrite(str(fp_wo_suffix) + ".png", frame)
                logging.info("Wrote " + str(fp_wo_suffix))

                # object json
                with open(str(fp_wo_suffix) + ".json", "w") as f:
                    json.dump(
                        {
                            "object_class": self.object_class,
                            "component_list": component_list,
                        },
                        f,
                        indent=2,
                    )
                self.collect_loop_data_list.append(
                    CollectLoopDataItem(
                        object_id=object_id,
                        filepath=str(fp_wo_suffix),
                        dt=datetime.datetime.now(),
                    )
                )
                self.update_average_collection_frequency()

                # upload via scp
                if sys.platform == "win32":
                    cmd = (
                        f'scp {str(fp_wo_suffix) + ".png"} '
                        + sorter.util.config_handler.ConfigHandler().get_param(
                            "vision_service_win32_scp_target"
                        )
                    )
                    return_code = os.system(cmd)
                    logging.info(f"SCP command: {cmd}")
                    logging.info(f"Return Code: {return_code}")

                # classifier
                # rel to data_dir
                relative_path = fp_wo_suffix.relative_to(
                    sorter.classification_service.config.data_dir_path
                )
                self.send_classification_request(
                    object_id, relative_path.with_suffix(".png")
                )

            # write count
            self.count_written += 1

            # coutout for viz
            self.detected_crop_low = (
                sorter.classification_service.crop_image.crop_image(frame, low=True)
            )
            self.detected_crop_high = (
                sorter.classification_service.crop_image.crop_image(frame, low=False)
            )
            self.last_pred_low_list = None
            self.last_pred_high_list = None

        # fps
        delta_sec = (
            datetime.datetime.now() - self.collect_loop_dt_last_frame
        ).total_seconds()
        fps = 1.0 / delta_sec if delta_sec > 0 else 1000
        self.collect_loop_smooth_fps = 0.9 * self.collect_loop_smooth_fps + 0.1 * fps

        # low fps
        if (
            self.collect_loop_smooth_fps < self.min_fps
            and self.collect_loop_frame_index > 10 * 30
        ):
            self.collect_loop_low_fps_frame_count += 1
        else:
            self.collect_loop_low_fps_frame_count = 0
        # stop, happened too often
        if self.collect_loop_low_fps_frame_count > 60:
            logging.error(
                f"Triggering Soft-EStop: Framerate too low for {self.collect_loop_low_fps_frame_count} frames"
                " - will miss part positions: {self.collect_loop_smooth_fps:.2f}fps"
            )
            self.soft_estop_enabled = True
        if not self.enable_visualization and self.collect_loop_frame_index % 30 == 0:
            logging.info(f"SmoothFps: {self.collect_loop_smooth_fps:.1f}fps")

        if self.enable_visualization:
            # bg box
            w = frame_viz.shape[1]
            top_box_height = 30
            x = 0
            y = 0
            sorter.vision_service.draw_bg_box.draw_bg_box(
                frame_viz, x, y, w, top_box_height
            )

            detector_stat = self.od.get_statistics()

            # top text
            if self.collection_mode == CollectionMode.TRAINING:
                col_mode_str = "TRAIN"
            elif self.collection_mode == CollectionMode.TESTING:
                col_mode_str = "TEST"
            elif self.collection_mode == CollectionMode.TRASH:
                col_mode_str = "TRASH"
            elif self.collection_mode == CollectionMode.INCONSISTENT:
                col_mode_str = "INC"
            elif self.collection_mode == CollectionMode.KEEP_INCORRECT:
                col_mode_str = "KIC"
            else:
                raise Exception("Unknown collection mode")
            msg = (
                "Label: "
                + self.object_class
                + "  Writing: "
                + ("False" if self.no_write else "True")
            )
            msg += f"  Scanned: {self.count_written}"
            msg += f'  Double: {detector_stat["count_double_object"]}'
            msg += f"  Mode: {col_mode_str}"
            msg += "  Net: " + (
                "True"
                if not self.disable_network and self.tcp_client.get_connected()
                else "False"
            )
            msg += "  Scanner: " + (
                "Busy" if self.collect_loop_last_frame_belt_busy else "Free"
            )
            msg += "  FPS: %.2f" % self.collect_loop_smooth_fps
            msg += f"  LB: {sec_since_last_busy:03.0f}s"
            # msg += f'  Frame: {self.collect_loop_frame_index:05d}'
            msg += f"  HM: {sorter.util.time_delta_format.time_delta_format(self.last_received_hour_meter_sec)}"
            msg += f"  PPM: {self.collect_loop_average_part_per_sec*60:.1f}"
            cv2.putText(
                frame_viz,
                msg,
                (10, 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
                2,
            )

            # object list
            w = 220
            margin = 10
            img_height = frame_viz.shape[0]
            h = img_height - 2 * margin - top_box_height
            x = frame_viz.shape[1] - w - margin
            y = top_box_height + margin
            sorter.vision_service.draw_bg_box.draw_bg_box(frame_viz, x, y, w, h)
            y = top_box_height + 3 * margin
            for line in self.make_object_list():
                cv2.putText(
                    frame_viz,
                    line,
                    (x + 10, y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (255, 255, 255),
                    1,
                    2,
                )
                y += 20

            self.draw_soft_estop(frame_viz)

            self.draw_classifier_result(frame_viz)

            # show
            window_name = "Vision Service"
            if self.enable_visualization_fullscreen:
                cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
                cv2.setWindowProperty(
                    window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN
                )

            cv2.imshow(window_name, frame_viz)
            if not self.enable_visualization_fullscreen:
                cv2.moveWindow(window_name, 50, 50)

            # keyboard input
            # http://www.asciitable.com/  (DEC column)
            k = cv2.waitKey(1)
            if k != -1:
                if k == 27:  # ESC
                    self.soft_estop_enabled = True
                elif k == 115 or k == 32:  # s, space
                    self.soft_estop_enabled = not self.soft_estop_enabled
                elif k == 99:  # c
                    if self.collection_mode == CollectionMode.TRASH:
                        self.collection_mode = CollectionMode.TRAINING
                    elif self.collection_mode == CollectionMode.TRAINING:
                        self.collection_mode = CollectionMode.TESTING
                    elif self.collection_mode == CollectionMode.TESTING:
                        self.collection_mode = CollectionMode.INCONSISTENT
                    elif self.collection_mode == CollectionMode.INCONSISTENT:
                        self.collection_mode = CollectionMode.KEEP_INCORRECT
                    elif self.collection_mode == CollectionMode.KEEP_INCORRECT:
                        self.collection_mode = CollectionMode.TRASH
                    else:
                        raise Exception("Unknown collection mode")
                elif k == ord("m"):  # m
                    self.enable_viz_mask = not self.enable_viz_mask
                elif k == 113:  # q, quit
                    cv2.destroyAllWindows()
                    return True
        # e-stop
        self.periodically_send_soft_estop_state()

        self.collect_loop_frame_index += 1
        self.collect_loop_dt_last_frame = datetime.datetime.now()
        return False

    def update_average_collection_frequency(self):
        last_N_items = self.collect_loop_data_list[-20:]  # last 20 items

        # deltas
        delta_sec_list = []
        for current, next in zip(last_N_items, last_N_items[1:]):
            delta_sec_list.append((next.dt - current.dt).total_seconds())

        # average
        self.collect_loop_average_part_per_sec = 0
        if len(delta_sec_list) > 0:
            average_sec = sum(delta_sec_list) / len(delta_sec_list)
            if average_sec > 0:
                self.collect_loop_average_part_per_sec = 1.0 / average_sec

    def draw_soft_estop(self, frame_viz):
        if self.soft_estop_enabled:
            cv2.putText(
                frame_viz,
                "Belt Stopped",
                (500, 400),
                cv2.FONT_HERSHEY_SIMPLEX,
                2,
                (0, 0, 255),
                3,
                2,
            )

    def send_classification_request(self, object_id, filepath: pathlib.Path):
        if self.disable_network:
            return

        if self.tcp_client.get_connected():
            # on win convert to linux path
            if sys.platform == "win32":
                filepath = pathlib.PurePosixPath(filepath)

            msg = b"CLF %d %s" % (object_id, bytes(str(filepath), "utf-8"))
            logging.info(f'Classification Request: "{str(msg, "utf-8")}"')
            self.tcp_client.send_msg(msg)

    def receive_classification_result(
        self,
        object_id: int,
        predicted_class: str,
        probability: float,
        uniqueness: float,
        average_process_time_sec: float,
        pred_low_list: list,
        pred_high_list: list,
    ):
        # find stored image
        item: CollectLoopDataItem
        found_item: CollectLoopDataItem = None
        for item in self.collect_loop_data_list:
            if item.object_id == object_id:
                found_item = item
        if found_item is None:
            raise Exception(
                f"Received classification result for object_id {object_id} which is not not in collect loop"
                " data list"
            )
        found_item.predicted_class = predicted_class
        found_item.probability = probability
        found_item.uniqueness = uniqueness
        found_item.average_process_time_sec = average_process_time_sec

        # visu
        self.last_pred_low_list = pred_low_list
        self.last_pred_high_list = pred_high_list

        # prediction into json
        json_fp = found_item.filepath + ".json"
        with open(json_fp) as f:
            data = json.load(f)

        # add prediction
        data["predicted_class"] = predicted_class
        data["pred_low_list"] = pred_low_list
        data["pred_high_list"] = pred_high_list
        logging.info(data)

        # write json
        with open(json_fp, "w") as f:
            json.dump(data, f, indent=2)
        logging.info(f"Json written {json_fp}.")

        # inconsistent mode - delete if consistent
        if self.collection_mode == CollectionMode.INCONSISTENT:
            inconsistent = (
                pred_low_list[0]["class"] != pred_high_list[0]["class"]
                or predicted_class.startswith("inc_")
                or predicted_class == "skip"
            )
            if not inconsistent:
                self.delte_img_and_json(found_item)

        # keep incorrect mode - delete if correct
        if self.collection_mode == CollectionMode.KEEP_INCORRECT:
            correct = self.object_class == predicted_class
            if correct:
                self.delte_img_and_json(found_item)

    def delte_img_and_json(self, found_item):
        fp = pathlib.Path(found_item.filepath + ".json")
        logging.info(f"Deleting {fp} ...")
        fp.unlink()

        fp = pathlib.Path(found_item.filepath + ".png")
        logging.info(f"Deleting {fp} ...")
        fp.unlink()

    def receive_hour_meter_value(self, hour_meter_sec):
        self.last_received_hour_meter_sec = hour_meter_sec

    def make_object_list(self):
        txt_list = ["Object List"]
        item: CollectLoopDataItem
        for item in self.collect_loop_data_list[-18:]:
            c = f"{item.object_id:03d}"
            c += (
                f" {item.predicted_class:<10}"
                if item.predicted_class is not None
                else f'{"-":^10}'
            )
            c += (
                f" {item.probability*100:3.0f}%"
                if item.probability is not None
                else f' {"-":^4}'
            )
            c += (
                f" {item.uniqueness:3.0f}"
                if item.uniqueness is not None
                else f' {"-":^3}'
            )
            c += (
                f" {item.average_process_time_sec:3.1f}s"
                if item.uniqueness is not None
                else f' {"-":^5}'
            )
            txt_list.append(c)
        return txt_list

    def periodically_send_soft_estop_state(self):
        """
        Re-Send periodically in case of connection broke
          - every N frames
          - changed
        """
        delta = self.collect_loop_frame_index - self.soft_estop_last_sent_frame_index
        changed = self.soft_estop_enabled_last_frame != self.soft_estop_enabled

        # notification
        if changed:
            self.notification_client.notify_soft_estop(self.soft_estop_enabled)

        # send STP
        if changed or delta > 5 * 30:
            # re-send
            if not self.disable_network and self.tcp_client.get_connected():
                if self.soft_estop_enabled:
                    self.tcp_client.send_msg(b"STP true")
                else:
                    self.tcp_client.send_msg(b"STP false")
            self.soft_estop_last_sent_frame_index = self.collect_loop_frame_index

        self.soft_estop_enabled_last_frame = self.soft_estop_enabled

    def handle_timeout_max_non_busy(self, belt_busy):
        if belt_busy:
            self.dt_belt_last_busy = datetime.datetime.now()

        # time since belt was busy
        sec_since_last_busy = (
            datetime.datetime.now() - self.dt_belt_last_busy
        ).total_seconds()

        # time since belt busy time msg was sent
        if self.dt_belt_busy_time_msg_sent is None:
            sec_since_last_msg = 1e10
        else:
            sec_since_last_msg = (
                datetime.datetime.now() - self.dt_belt_busy_time_msg_sent
            ).total_seconds()

        send_belt_busy_msg = (
            sec_since_last_busy > self.max_sec_since_last_busy
            and sec_since_last_msg > self.time_since_last_busy_msg_interval_sec
        )

        if send_belt_busy_msg:
            # send notification
            logging.info("Timeout max non-busy: E-Stop + sending notify ...")

            self.notification_client.notify_timeout_max_non_busy(sec_since_last_busy)
            self.dt_belt_busy_time_msg_sent = datetime.datetime.now()

            # estop
            self.soft_estop_enabled = True

        return sec_since_last_busy

    def draw_classifier_result(self, frame_viz):
        # mask viz mode
        if self.enable_viz_mask:
            return

        cutout_size = 224
        margin = 10
        img_width = frame_viz.shape[1]
        object_list_width = 220
        box_width = int(img_width - 3 * margin - object_list_width)
        box_height = cutout_size + 2 * margin
        box_left_x = margin
        box_y = frame_viz.shape[0] - margin - box_height

        sorter.vision_service.draw_bg_box.draw_bg_box(
            frame_viz, box_left_x, box_y, box_width, box_height
        )

        if self.detected_crop_low is not None:
            self.blit(frame_viz, self.detected_crop_low, 2 * margin, box_y + margin)
            self.blit(
                frame_viz,
                self.detected_crop_high,
                3 * margin + cutout_size,
                box_y + margin,
            )

        if self.last_pred_low_list is not None and self.last_pred_high_list is not None:
            bar_height = 20
            txt_bellow_bar_y_offset = 35
            vertical_step = 50

            # low
            for cue in ["low"]:  # , 'high'
                bar_x = 4 * margin + 2 * cutout_size
                if cue == "low":
                    pred_list = self.last_pred_low_list
                else:
                    pred_list = self.last_pred_high_list
                bar_y = box_y + margin
                bar_max_width = box_width - (4 * margin + 2 * cutout_size)
                for i in range(3):
                    assert 0 <= pred_list[i]["probability"] <= 1
                    bar_width = int(pred_list[i]["probability"] * float(bar_max_width))
                    cv2.rectangle(
                        frame_viz,
                        (bar_x, bar_y),
                        (bar_x + bar_width, bar_y + bar_height),
                        (255, 255, 255),
                        thickness=-1,
                    )
                    cv2.putText(
                        frame_viz,
                        pred_list[i]["class"],
                        (bar_x, bar_y + txt_bellow_bar_y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.4,
                        (255, 255, 255),
                        1,
                        2,
                        bottomLeftOrigin=False,
                    )
                    bar_y += vertical_step

    def blit(self, frame_viz, small, x, y):
        frame_viz[y : y + small.shape[0], x : x + small.shape[1]] = small
