import json
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
from sorter.util.camera import read_camera_parameters

if __name__ == "__main__":
    # parse command line arguments
    parser = sorter.util.argument_parser.ArgumentParser(
        description="Video capture tool"
    )
    # argument for folder to read
    parser.add_argument("--folder", required=True)
    parser.add_argument("--test", required=False, action="store_true")
    args = parser.parse_args()

    data_folder_path = pathlib.Path(args.folder)
    logging.info(
        f"Reading objpoints.npy and imgpoints.npy from folder {data_folder_path} ..."
    )

    # extract datetime from calibration_YYYY-MM-DD_HH-MM in data_folder_path dirname or exit with error if not matches
    try:
        calibration_datetime_str = data_folder_path.name.replace("calibration_", "")
        calibration_datetime = datetime.strptime(
            calibration_datetime_str, "%Y-%m-%d_%H-%M"
        )
    except ValueError:
        logging.error(
            f"Folder name {data_folder_path.name} does not match expected format 'calibration_YYYY-MM-DD_HH-MM'"
        )
        sys.exit(1)
    logging.info(f"Extracted datetime: {calibration_datetime}")
    calibration_fp = data_folder_path / (
        "calibration_" + calibration_datetime_str + ".json"
    )

    # get first image
    first_image_path = next(data_folder_path.glob("*.png"))
    img = cv2.imread(str(first_image_path))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img_size = gray.shape[::-1]

    if not args.test:
        # read objpoints.npy and imgpoints.npy from data_folder_path folder
        objpoints = np.load(data_folder_path / "objpoints.npy")
        imgpoints = np.load(data_folder_path / "imgpoints.npy")

        # calibrate camera
        ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
            objpoints, imgpoints, img_size, None, None
        )

        logging.info("Calibration completed and saved to calibration.json")
        logging.info(f"Camera matrix:\n{mtx}")
        logging.info(f"Distortion coefficients:\n{dist}")

        # save calibration result
        calibration_data = {
            "mtx": mtx.tolist(),
            "dist": dist.tolist(),
            "rvecs": [rvec.tolist() for rvec in rvecs],
            "tvecs": [tvec.tolist() for tvec in tvecs],
        }

        logging.info("Writing calibration data to json file ...")
        with open(str(calibration_fp), "w+") as f:
            json.dump(calibration_data, f, indent=2)

    if args.test:
        # read the calibration parameters again with method read_camera_parameters for test
        mtx_read, dist_read = read_camera_parameters(calibration_fp)
        logging.info(f"Read camera matrix:\n{mtx_read}")
        logging.info(f"Read distortion coefficients:\n{dist_read}")

        # undistort the first image and show with imshow
        undistorted_img = cv2.undistort(img, mtx_read, dist_read, None, mtx_read)
        cv2.imshow("Original Image", img)
        cv2.imshow("Undistorted Image", undistorted_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
