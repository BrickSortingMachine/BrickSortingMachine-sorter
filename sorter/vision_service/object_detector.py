import dataclasses
import logging

import cv2
import numpy as np

import sorter.notification_service.notification_client


@dataclasses.dataclass
class ObjectDetectorStatistics:
    count_trigger: int = 0
    count_multiple_objects: int = 0
    count_inhibited: int = 0

    def __iter__(self):
        """
        For unpacking
        """
        yield from dataclasses.astuple(self)


def create_mask(shape, A, B):
    """
    Function to create a mask based on points A and B
    """
    mask = np.ones(shape, dtype=np.uint8)
    for y in range(shape[0]):
        for x in range(shape[1]):
            result = (B[1] - A[1]) * x - (B[0] - A[0]) * y + B[0] * A[1] - A[0] * B[1]
            if result > 0:
                mask[y, x] = 0
    return mask


def blit_img(dst, src, offset_x, offset_y):
    dst[
        offset_y : (offset_y + src.shape[0]), offset_x : (offset_x + src.shape[1])
    ] = src


class ObjectDetector:
    def __init__(
        self,
        notification_client: sorter.notification_service.notification_client.NotificationClient,
    ) -> None:
        # bg model
        self.backSub = cv2.createBackgroundSubtractorMOG2(
            history=5000, varThreshold=400, detectShadows=False
        )  # 30pfs

        # busy area
        self.busy_area_min_x = 150
        self.busy_area_max_x = 1200
        self.busy_area_min_y = 400
        self.busy_area_max_y = 700

        # trigger area
        self.trigger_area_min_x = 350
        self.trigger_area_max_x = 400
        self.trigger_area_min_y = 410
        self.trigger_area_max_y = 690

        # frame count after start where bg learns and no components are detected
        self.start_up_inhibition = 5

        # assume first frame is trigger because background model needs to learn first
        self.last_trigger_frame = 0

        # do not retrigger within this frame count time frame since last trigger
        self.trigger_frame_count_inhibition = 50

        self.last_belt_busy_frame = -1e5
        self.belt_busy_inhibition_frame_count = 20

        self.count_triggered = 0
        self.count_double_object = 0

        self.notification_client = notification_client

        # mask out corners
        self.bg_mask_height = self.busy_area_max_y - self.busy_area_min_y
        self.bg_mask_width = self.busy_area_max_x - self.busy_area_min_x
        self.corner_lines = [
            (
                (self.bg_mask_width - 50, 0),
                (self.bg_mask_width, 50),
            ),  # top right corner
            (
                (self.bg_mask_width, self.bg_mask_height - 80),
                (self.bg_mask_width - 100, self.bg_mask_height),
            ),  # bottom right
        ]
        self.overall_mask = None
        self.pre_compute_corner_bg_substraction_mask()

    def pre_compute_corner_bg_substraction_mask(self):
        self.overall_mask = np.ones(
            (self.bg_mask_height, self.bg_mask_width), dtype=np.uint8
        )

        # mask based on line
        for A, B in self.corner_lines:
            mask = create_mask((self.bg_mask_height, self.bg_mask_width), A, B)
            self.overall_mask &= mask

    def process_frame(
        self, frame_index, frame, enable_visualization=False, enable_viz_mask=False
    ):
        # create cutout
        bg_subtraction_roi = frame[
            self.busy_area_min_y : self.busy_area_max_y,
            self.busy_area_min_x : self.busy_area_max_x,
        ]

        # subtract BG
        fg_mask = self.backSub.apply(bg_subtraction_roi, None, 0.001)
        if enable_viz_mask:
            debug_viz_mask_after_bg_model = fg_mask.copy()

        # mask out corners
        fg_mask *= self.overall_mask

        # close objects
        kernel = np.ones((13, 13), np.uint8)
        closing = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
        if enable_viz_mask:
            debug_viz_mask_after_close = closing.copy()

        # open, remove small objects
        closing = cv2.morphologyEx(closing, cv2.MORPH_OPEN, kernel)
        if enable_viz_mask:
            debug_viz_mask_after_open = closing.copy()

        # connected components
        connectivity = 4  # 8
        output = cv2.connectedComponentsWithStats(closing, connectivity, cv2.CV_32S)
        (numLabels, labels, stats, centroids) = output

        # viz image in color
        if enable_visualization:
            # gray image + color highlight
            frame_viz_mono = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            frame_viz = cv2.cvtColor(frame_viz_mono, cv2.COLOR_GRAY2BGR)

            if enable_viz_mask:
                # viz individual steps
                debug_viz_mask_after_bg_model = cv2.cvtColor(
                    debug_viz_mask_after_bg_model, cv2.COLOR_GRAY2BGR
                )
                debug_viz_mask_after_close = cv2.cvtColor(
                    debug_viz_mask_after_close, cv2.COLOR_GRAY2BGR
                )
                debug_viz_mask_after_open = cv2.cvtColor(
                    debug_viz_mask_after_open, cv2.COLOR_GRAY2BGR
                )

                # big bottom window
                frame_viz[
                    self.busy_area_min_y : self.busy_area_max_y,
                    self.busy_area_min_x : self.busy_area_max_x,
                ] = debug_viz_mask_after_open

                new_dimensions = (
                    int(self.bg_mask_width * 0.5),
                    int(self.bg_mask_height * 0.5),
                )
                debug_viz_mask_after_bg_model = cv2.resize(
                    debug_viz_mask_after_bg_model,
                    new_dimensions,
                    interpolation=cv2.INTER_LINEAR,
                )
                debug_viz_mask_after_close = cv2.resize(
                    debug_viz_mask_after_close,
                    new_dimensions,
                    interpolation=cv2.INTER_LINEAR,
                )
                debug_viz_mask_after_open = cv2.resize(
                    debug_viz_mask_after_open,
                    new_dimensions,
                    interpolation=cv2.INTER_LINEAR,
                )

                cv2.putText(
                    debug_viz_mask_after_bg_model,
                    "(1) After Bg Model",
                    (0, 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    1,
                    2,
                )
                cv2.putText(
                    debug_viz_mask_after_close,
                    "(2) After Close - consistent inside objects",
                    (0, 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    1,
                    2,
                )
                cv2.putText(
                    debug_viz_mask_after_open,
                    "(3) After Open - remove thin objects",
                    (0, 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    1,
                    2,
                )

                blit_img(frame_viz, debug_viz_mask_after_bg_model, 50, 50)
                blit_img(
                    frame_viz, debug_viz_mask_after_close, 100 + new_dimensions[0], 50
                )
                blit_img(
                    frame_viz,
                    debug_viz_mask_after_open,
                    100 + new_dimensions[0],
                    70 + new_dimensions[1],
                )

                # plot corner lines
                for A, B in self.corner_lines:
                    A_transformed = (
                        A[0] + self.busy_area_min_x,
                        A[1] + self.busy_area_min_y,
                    )
                    B_transformed = (
                        B[0] + self.busy_area_min_x,
                        B[1] + self.busy_area_min_y,
                    )
                    cv2.line(frame_viz, A_transformed, B_transformed, (0, 0, 255), 1)

        else:
            frame_viz = None

        # loop components (1 to skip BG comp)
        component_list = []
        if frame_index > self.start_up_inhibition:
            for i in range(1, numLabels):
                # offset from background substraction roi to full image
                x = stats[i, cv2.CC_STAT_LEFT] + self.busy_area_min_x
                y = stats[i, cv2.CC_STAT_TOP] + self.busy_area_min_y

                w = stats[i, cv2.CC_STAT_WIDTH]
                h = stats[i, cv2.CC_STAT_HEIGHT]
                area = stats[i, cv2.CC_STAT_AREA]
                (cx, cy) = centroids[i]

                # check for overlap component and trigger area
                if cx == cx and cy == cy:
                    component_list.append(
                        {
                            "x": int(x),
                            "y": int(y),
                            "w": int(w),
                            "h": int(h),
                            "area": float(area),
                            "cx": float(cx),
                            "cy": float(cy),
                        }
                    )

        # belt busy
        if len(component_list) > 0:
            self.last_belt_busy_frame = frame_index
        belt_busy = (
            frame_index - self.last_belt_busy_frame
            < self.belt_busy_inhibition_frame_count
        )

        # trigger
        trigger = self.eval_trigger(frame_index, component_list)

        if enable_visualization:
            # viz roi
            cv2.rectangle(
                frame_viz,
                (self.busy_area_min_x, self.busy_area_min_y),
                (self.busy_area_max_x, self.busy_area_max_y),
                (70, 70, 70),
                1,
            )

            # viz trigger area
            cv2.rectangle(
                frame_viz,
                (self.trigger_area_min_x, self.trigger_area_min_y),
                (self.trigger_area_max_x, self.trigger_area_max_y),
                (140, 140, 140),
                1,
            )

            # object rectangle
            for comp in component_list:
                # copy in color cutout
                if not enable_viz_mask:
                    # mask is in bg subtraction ROI coordinates
                    comp_x_mask = comp["x"] - self.busy_area_min_x
                    comp_y_mask = comp["y"] - self.busy_area_min_y
                    mask_cutout = closing[
                        comp_y_mask : comp_y_mask + comp["h"],
                        comp_x_mask : comp_x_mask + comp["w"],
                    ]

                    color_cutout = frame[
                        comp["y"] : comp["y"] + comp["h"],
                        comp["x"] : comp["x"] + comp["w"],
                    ]

                    # this is a reference into the viz_image
                    cutout = frame_viz[
                        comp["y"] : comp["y"] + comp["h"],
                        comp["x"] : comp["x"] + comp["w"],
                    ]
                    cutout[mask_cutout > 0] = color_cutout[mask_cutout > 0]

                # draw rectanle
                cv2.rectangle(
                    frame_viz,
                    (comp["x"], comp["y"]),
                    (comp["x"] + comp["w"], comp["y"] + comp["h"]),
                    (0, 255, 0),
                    1,
                )

        return trigger, frame_viz, component_list, belt_busy

    def eval_trigger(self, frame_index, component_list):
        trigger = False

        for comp in component_list:
            a_min_x = self.trigger_area_min_x
            a_min_y = self.trigger_area_min_y
            a_max_x = self.trigger_area_max_x
            a_max_y = self.trigger_area_max_y

            c_min_x = comp["x"]
            c_max_x = comp["x"] + comp["w"]
            c_min_y = comp["y"]
            c_max_y = comp["y"] + comp["h"]

            # left edge of component must be in area x (not just overlap)
            left_edge_in_area = c_min_x >= a_min_x

            # component overlaps area
            c_overlaps_area = (
                c_max_x > a_min_x
                and c_min_x < a_max_x
                and c_max_y > a_min_y
                and c_min_y < a_max_y
            )

            # time inhibition
            is_inhibited = (
                frame_index - self.last_trigger_frame
            ) < self.trigger_frame_count_inhibition

            if not is_inhibited:
                # obj somewhere in area
                if c_overlaps_area:
                    # inhibt
                    self.last_trigger_frame = frame_index

                    # object in trigger area
                    if left_edge_in_area:
                        # max 1 obj in roi
                        if len(component_list) > 1:
                            logging.warning(
                                "Obj in trigger but total %d obj present"
                                % len(component_list)
                            )
                            self.count_double_object += 1
                            if self.notification_client is not None:
                                self.notification_client.notify_double_part_scanned()
                        else:
                            trigger = True
                            logging.info("Triggered")
                            self.count_triggered += 1
        return trigger

    def currently_inhibited(self, frame_index: int):
        inhib_delta = frame_index - self.last_trigger_frame
        return inhib_delta < self.trigger_frame_count_inhibition

    def get_statistics(self):
        return {
            "count_triggered": self.count_triggered,
            "count_double_object": self.count_double_object,
        }
