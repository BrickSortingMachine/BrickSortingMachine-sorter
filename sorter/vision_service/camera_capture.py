import logging
import math
import os
import sys

import cv2
import tqdm

tqdm.tqdm.monitor_interval = 0  # switch off unstopped monitor thread
import subprocess

import sorter.vision_service.capture_multithreaded


class CameraCapture:
    def __init__(
        self,
        camera_name: str,
        recording=None,
        dummy_max_frame_count=None,
        enable_multithread=False,
    ):
        # sanitize name
        camera_name_list = ["fisheye", "logitech_c920"]
        if camera_name not in camera_name_list:
            raise Exception(
                f'Camera name {camera_name} not in list {",".join(camera_name_list)}'
            )

        # dummy mode
        self.pre_recorded_enabled = recording is not None

        # dummy mode - loop recoring
        self.pre_recorded_loop_count = 1  # -1 is loop forever

        # how often the focus was initialized
        self.focus_initiatized_count = 0

        if not self.pre_recorded_enabled:
            # name -> camera_index
            camera_index = self.get_camera_index(camera_name)
            self.exposure_list = self.get_exposure_list(camera_name)
            if camera_name == "logitech_c920":
                self.focus = 118
                self.exposure_level = 5
                fps = 15
                self.width = 1280
                self.height = 720
            elif camera_name == "fisheye":
                self.focus = 0  # has no focus
                self.exposure_level = 0
                fps = 30
                self.width = 1280
                self.height = 720
            else:
                raise Exception(
                    f"No default values defined for camera_name={camera_name}"
                )

            # initialize video grabber
            logging.info(
                f'Connecting camera "{camera_name}" at index {camera_index} ...'
            )

            if sys.platform == "win32":
                self.video = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
                self.video.set(
                    cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc("m", "j", "p", "g")
                )
                self.video.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.video.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

            elif sys.platform == "linux":
                self.video = cv2.VideoCapture(camera_index)
                self.video.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.video.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.video.set(
                    cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc("M", "J", "P", "G")
                )

            else:
                raise NotImplementedError()

            self.video.set(cv2.CAP_PROP_FPS, fps)

            if self.video is None or not self.video.isOpened():
                raise Exception("Camera device not available")

            if sys.platform == "linux":
                # focus
                self.video.set(cv2.CAP_PROP_AUTOFOCUS, 0)
                self.video.set(cv2.CAP_PROP_FOCUS, self.focus)

                # exposure => lightness / motionblur
                # working with v4l2
                self.video.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # 1 manual, 3 auto
                self.video.set(
                    cv2.CAP_PROP_EXPOSURE, self.exposure_list[self.exposure_level]
                )

            else:
                logging.warning(
                    "CameraCapture: Manual exposure/focus operating system not implemented yet"
                )

            # unused parameters
            # gain:       self.video.get(cv2.CAP_PROP_GAIN),
            # brightness: self.video.get(cv2.CAP_PROP_BRIGHTNESS),
            # saturation: self.video.get(cv2.CAP_PROP_SATURATION),

            # capture thread
            self.enable_multithread = enable_multithread
            if self.enable_multithread:
                raise Exception("Multithreaded capturing not supported anymore")
                self.capture_multithreaded = (
                    sorter.capture_multithreaded.CaptureMultithreaded(self.video)
                )

        else:
            # no camera mode / dummy mode
            data_folder_path = recording

            logging.info("Loading image sequence ...")
            self.dummy_frame_index = 0
            self.dummy_frame_list = []

            # is dummy images downloaded?
            if not os.path.isdir(data_folder_path):
                raise Exception(
                    f'Trying to load "{data_folder_path}". Test data not available - '
                    "please run tools/download_unpack_test_data.py"
                )

            for frame_index, fn in enumerate(
                tqdm.tqdm(sorted(os.listdir(data_folder_path)))
            ):
                # limit frames to load
                if dummy_max_frame_count is None or frame_index < dummy_max_frame_count:
                    self.dummy_frame_list.append(
                        cv2.imread(os.path.join(data_folder_path, fn))
                    )
            logging.info("Complete.")

        self.frame_index = 0

    def set_focus(self, focus):
        self.focus = focus
        self.video.set(cv2.CAP_PROP_FOCUS, self.focus)

    def set_exposure_level(self, exposure_level):
        self.exposure_level = exposure_level
        exposure = self.exposure_list[exposure_level]
        logging.info(f"Exposure Level: {exposure_level}  Exposure: {exposure}")
        self.video.set(cv2.CAP_PROP_EXPOSURE, exposure)
        r = self.video.get(cv2.CAP_PROP_EXPOSURE)
        if r != exposure:
            logging.error(f"Exposure not set set={exposure} get={r}")
        else:
            logging.info(f"Exposure set={exposure} successful")

    def capture(self):
        if not self.pre_recorded_enabled:
            if not self.enable_multithread:
                ret, frame = self.video.read()
                assert ret
            else:
                frame = self.capture_multithreaded.get_next_frame()

            # set exp,focus 10 frames
            if self.focus_initiatized_count < 5:
                self.focus_initiatized_count += 1
                self.set_focus(self.focus)
                self.set_exposure_level(self.exposure_level)

            # upscale on win32
            if sys.platform == "win32":
                captured_height, captured_width = frame.shape[:2]
                assert captured_width == 640
                assert captured_height == 480

                # crop height to correct aspect ratio
                target_ratio = 1280 / 720
                crop_height = math.floor(640 / target_ratio)
                vertical_crop_offset = 60
                frame = frame[
                    vertical_crop_offset : (vertical_crop_offset + crop_height), :
                ]

                frame = cv2.resize(
                    frame, (self.width, self.height), interpolation=cv2.INTER_CUBIC
                )
                if self.frame_index % 50 == 0:
                    logging.warning("Upscalling images on win32")

            # assert img dimensions
            captured_height, captured_width = frame.shape[:2]
            assert captured_width == self.width
            assert captured_height == self.height

            self.frame_index += 1

            return frame

        else:
            # pick dummy frame
            current_dummy_frame = self.dummy_frame_list[self.dummy_frame_index]

            # increment and wrap dummy frame index
            self.dummy_frame_index += 1
            if self.dummy_frame_index >= len(self.dummy_frame_list):
                if (
                    self.pre_recorded_loop_count > 0
                    or self.pre_recorded_loop_count == -1
                ):  # -1 loop forever
                    # reset rec
                    self.dummy_frame_index = 0

                    # decr remaining loops
                    self.pre_recorded_loop_count -= 1
                else:
                    # not looping, tell caller that ended
                    return None

            return current_dummy_frame.copy()

    def get_camera_index(self, camera_name):
        if sys.platform == "linux":
            r = subprocess.run(["v4l2-ctl", "--list-devices"], stdout=subprocess.PIPE)
            if r.returncode != 0:
                raise Exception(
                    'No camera connected or v4l2-ctl not installed. Connect camera or install via "sudo apt install v4l-utils"'
                )
            device_list = self.parse_v4l2_ctl_output(str(r.stdout, "utf-8").split("\n"))
            match_device_list = list(
                filter(lambda d: d["short_name"].startswith(camera_name), device_list)
            )
            if len(match_device_list) != 1:
                raise Exception("Camera device not found")
            camera_index = match_device_list[0]["index_list"][0]
        elif sys.platform == "win32":
            device_list = self.parse_win_device_list()
            match_device_list = list(
                filter(lambda d: d["short_name"].startswith(camera_name), device_list)
            )
            if len(match_device_list) != 1:
                raise Exception(f'Camera device "{camera_name}" not found')
            camera_index = match_device_list[0]["index_list"][0]
        else:
            raise Exception("CameraCapture: Other operating system not implemented yet")

        return camera_index

    def parse_v4l2_ctl_output(self, v4l2_output_list):
        v4l2_output_list = [s.strip() for s in v4l2_output_list]
        """
            'HD USB Camera (usb-0000:00:14.0-1):'
            '/dev/video0'
            '/dev/video1'
            '/dev/media0'
            ''
            'HD Pro Webcam C920 (usb-0000:00:14.0-2):'
            '/dev/video2'
            '/dev/video3'
            '/dev/media1'
            ''
            ''
        """

        # add at least 1 empty line at end
        v4l2_output_list.append("")

        in_device = False
        new_device_name = None
        path_list = []
        index_list = []
        device_list = []

        s: str
        for s in v4l2_output_list:
            if not in_device:
                if s.startswith("/"):
                    in_device = True
            else:
                if not s.startswith("/"):
                    # device completed

                    if new_device_name.startswith("HD Pro Webcam C920"):
                        short_name = "logitech_c920"
                    elif new_device_name.startswith("HD USB Camera"):
                        short_name = "fisheye"
                    else:
                        raise Exception(f"No camera shortname for {new_device_name}")

                    device_list.append(
                        {
                            "name": new_device_name,
                            "short_name": short_name,
                            "path_list": path_list,
                            "index_list": index_list,
                        }
                    )

                    in_device = False

            if not in_device:
                new_device_name = s
                path_list = []
                index_list = []
            else:
                path_list.append(s)
                if s.startswith("/dev/video"):
                    index_list.append(int(s[10:]))

        return device_list

    def parse_win_device_list(self):
        import device

        device_list = device.getDeviceList()

        result = []
        for index, d in enumerate(device_list):
            logging.info(f"  {index:02d} {d[0]}")
            if d[0] == "HD Pro Webcam C920":
                result.append(
                    {
                        "name": d[0],
                        "short_name": "logitech_c920",
                        "path_list": [],
                        "index_list": [index],
                    }
                )
            elif d[0] == "HD USB Camera":
                result.append(
                    {
                        "name": d[0],
                        "short_name": "fisheye",
                        "path_list": [],
                        "index_list": [index],
                    }
                )
            elif d[0] == "OBS Virtual Camera":
                # OBS cam
                pass
            elif d[0] == "HP HD Camera":
                # OBS cam
                pass
            else:
                raise Exception(f"Unknown capture device: {d[0]}")
        return result

    def get_exposure_list(self, camera_name):
        # logitech cam: dark->bright 3,4-7,8-15,16-31,32-63,64-
        # fisheye cam: dark->bright 4-8,9-18,19-38,39-77,78-

        if sys.platform == "linux":
            if camera_name == "logitech_c920":
                exposure_list = [3, 4, 8, 16, 32, 64]
            elif camera_name == "fisheye":
                exposure_list = [4, 9, 19, 39, 78]
            else:
                raise NotImplementedError(
                    f"Exposure list not defined for camera_name={camera_name}"
                )

        elif sys.platform == "win32":
            if camera_name == "fisheye":
                exposure_list = [-11, -10, -8, -7, -6, -5, -4, -3, -2]
            else:
                raise NotImplementedError(
                    f"Exposure list not defined for camera_name={camera_name}"
                )

        else:
            raise NotImplementedError(f'Unknown platform "{sys.platform}"')

        return exposure_list

    def get_focus(self):
        return self.focus

    def get_exposure(self):
        return self.exposure_level

    def set_pre_recorded_loop_count(self, pre_recorded_loop_count):
        self.pre_recorded_loop_count = pre_recorded_loop_count
