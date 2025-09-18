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
    args = parser.parse_args()

    # capture device
    device = sorter.vision_service.camera_capture.CameraCapture("fisheye")

    # data file paths
    data_folder_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data")
    )

    while True:
        frame = device.capture()

        cv2.imshow("Video Capture", frame)
        k = cv2.waitKey(1)
        if k != -1:
            if k == 27 or k == ord("q"):  # ESC, q
                cv2.destroyAllWindows()
                break


