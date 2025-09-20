import logging
import os
import pathlib
import sys
from datetime import datetime

import cv2
import numpy as np

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

number_of_inner_corners_per_row = 9
number_of_inner_corners_per_column = 6

if __name__ == "__main__":
    # parse command line arguments
    parser = sorter.util.argument_parser.ArgumentParser(
        description="Video capture tool"
    )
    args = parser.parse_args()

    # capture device
    device = sorter.vision_service.camera_capture.CameraCapture("fisheye")

    # storage folder data/calibration_YYYY-MM-DD_HH-MM
    data_folder_path = (
        pathlib.Path(__file__).parents[1]
        / "data"
        / ("calibration_" + datetime.now().strftime("%Y-%m-%d_%H-%M"))
    )
    data_folder_path.mkdir(parents=True, exist_ok=True)

    # termination criteria
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

    # prepare object points, like (0,0,0), (1,0,0), (2,0,0) ....,(6,5,0)
    objp = np.zeros(
        (number_of_inner_corners_per_row * number_of_inner_corners_per_column, 3),
        np.float32,
    )
    objp[:, :2] = np.mgrid[
        0:number_of_inner_corners_per_row, 0:number_of_inner_corners_per_column
    ].T.reshape(-1, 2)

    frame_counter = 0
    # Arrays to store object points and image points from all the images.
    objpoints = []  # 3d point in real world space
    imgpoints = []  # 2d points in image plane.
    while True:
        frame = device.capture()

        cv2.imshow("Video Capture", frame)
        k = cv2.waitKey(1)
        if k != -1:
            if k == 27 or k == ord("q"):  # ESC, q
                cv2.destroyAllWindows()
                break

            elif k == ord("c"):  # c
                logging.info("Detecting checkerboard")
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # Find the chess board corners
                ret, corners = cv2.findChessboardCorners(
                    gray,
                    (
                        number_of_inner_corners_per_row,
                        number_of_inner_corners_per_column,
                    ),
                )

                # If found, add object points, image points (after refining them)
                if ret:
                    # write frame
                    cv2.imwrite(
                        str(data_folder_path / f"{frame_counter:03d}.png"), frame
                    )
                    frame_counter += 1

                    objpoints.append(objp)

                    corners2 = cv2.cornerSubPix(
                        gray, corners, (11, 11), (-1, -1), criteria
                    )
                    imgpoints.append(corners2)

                    # Draw and display the corners
                    cv2.drawChessboardCorners(
                        frame,
                        (
                            number_of_inner_corners_per_row,
                            number_of_inner_corners_per_column,
                        ),
                        corners2,
                        ret,
                    )
                    cv2.imshow("Video Capture", frame)
                    cv2.waitKey(1000)
                    logging.info("Checkerboard found")

                    # write objpoints and imgpoints as json into same folder
                    np.save(data_folder_path / "objpoints.npy", np.array(objpoints))
                    np.save(data_folder_path / "imgpoints.npy", np.array(imgpoints))

                else:
                    logging.error("No checkerboard found")
