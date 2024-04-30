import logging
import os
import os.path
import sys
from datetime import datetime

import cv2

logging.basicConfig(
    format="%(levelname)s %(asctime)s %(filename)s:%(lineno)d %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.DEBUG,
)

# add robolab folder to python path
p = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(p)

import sorter.util.argument_parser
import sorter.vision_service.camera_capture

if __name__ == "__main__":
    # parse command line arguments
    parser = sorter.util.argument_parser.ArgumentParser(
        description="Video capture tool"
    )
    parser.add_argument("--camera_name", required=True)
    parser.add_argument("--rec_suffix", required=True)
    args = parser.parse_args()

    if args.rec_suffix not in ["png", "jpg"]:
        logging.error('--rec_suffix must be either "png" or "jpg"')
        sys.exit(1)

    # capture device
    device = sorter.vision_service.camera_capture.CameraCapture(args.camera_name)

    # data file paths
    data_folder_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data")
    )

    dt_last_frame = datetime.now()
    frame_index = 0
    scale_percent = 100  # percent of original size
    enable_background_subtraction_test = False

    enable_recording = False
    enable_recording_last_frame = False
    recording_frame_list = []
    recording_name = None
    vertical_crop_offset = 0

    def print_help_message(device: sorter.vision_service.camera_capture.CameraCapture):
        print("Usage:")
        print("  [ESC] To Exit")
        print("  [Space] Start/stop recording")
        print("  [t] Save image")
        print("  [r] Focus far      [f] Focus near")
        print("  [e] Exposure +     [d] Exposure -")
        print("  [o] Crop Offset Up [l] Crop Offset Down")
        print("Focus:                %+4d" % device.get_focus())
        print("Exposure-Level:       %d" % device.get_exposure())
        print("Vertical Crop Offset: %d" % vertical_crop_offset)
        print(" ")

    print_help_message(device)

    while True:
        frame = device.capture()

        # recording
        # start
        if enable_recording and not enable_recording_last_frame:
            # clear buffer
            recording_frame_list = []
            recording_name = "rec_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            logging.info("Recording %s started ..." % recording_name)
        # running
        if enable_recording:
            recording_frame_list.append(frame)
            logging.info(
                "Recording buffer size: #%d,  %dMB"
                % (len(recording_frame_list), len(recording_frame_list) * 3.07)
            )
        # stopped
        if not enable_recording and enable_recording_last_frame:
            logging.info("Recording stopped. Saving ...")
            rec_dirpath = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "data", recording_name)
            )

            # create rec dir
            os.mkdir(rec_dirpath)

            # write all frames
            for index, rec_frame in enumerate(recording_frame_list):
                filepath = os.path.join(
                    rec_dirpath, "frame_%06d" % index + "." + args.rec_suffix
                )
                cv2.imwrite(filepath, rec_frame)
                logging.info(
                    "Wrote frame %d / %d." % (index, len(recording_frame_list))
                )
            logging.info("Writing completed.")

            # free memory
            recording_frame_list = []

        enable_recording_last_frame = enable_recording

        # fps
        delta_time = datetime.now() - dt_last_frame
        fps = 1 / delta_time.total_seconds()
        dt_last_frame = datetime.now()

        # crop in camera.py (normally it is cropped in camera_capture.py)
        # target_ratio = 1280 / 720
        # crop_height = math.floor(640 / target_ratio)
        # frame = frame[vertical_crop_offset:(vertical_crop_offset + crop_height), :]

        if frame_index % 100 == 0:
            logging.info("FPS: %.2ffps" % fps)
        cv2.imshow("Video Capture", frame)

        # keyboard input
        # http://www.asciitable.com/  (DEC column)
        k = cv2.waitKey(1)
        if k != -1:
            if k == 27 or k == ord("q"):  # ESC, q
                cv2.destroyAllWindows()
                break

            # focus
            elif k == 114:  # r
                focus = device.get_focus() - 1
                focus = max(0, min(255, focus))
                device.set_focus(focus)
                print_help_message(device)
            elif k == 102:  # f
                focus = device.get_focus() + 1
                focus = max(0, min(255, focus))
                device.set_focus(focus)
                print_help_message(device)

            # exposure
            elif k == 101:  # e
                exposure = device.get_exposure() + 1
                exposure = max(-200, min(200, exposure))
                device.set_exposure_level(exposure)
                print_help_message(device)

            elif k == 100:  # d
                exposure = device.get_exposure() - 1
                exposure = max(-200, min(200, exposure))
                device.set_exposure_level(exposure)
                print_help_message(device)

            # capture frame
            elif k == 116:  # t
                filename = (
                    "capture_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".png"
                )
                filepath = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), filename)
                )
                cv2.imwrite(filepath, frame)
                print("Wrote image to %s ..." % filepath)

            # start/stop recording
            elif k == 32:
                enable_recording = not enable_recording

            # vertical crop offset
            elif k == ord("o"):
                vertical_crop_offset -= 10
                vertical_crop_offset = max(0, vertical_crop_offset)
                print_help_message(device)
            elif k == ord("l"):
                vertical_crop_offset += 10
                print_help_message(device)

            # hide alt+tab warnings
            elif k == 233:
                pass
            else:
                print("Unused key: %d" % k)

        frame_index += 1
