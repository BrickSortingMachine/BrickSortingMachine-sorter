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
import sorter.vision_service.camera_capture

if __name__ == "__main__":
    # parse command line arguments
    parser = sorter.util.argument_parser.ArgumentParser(
        description="Video capture tool"
    )
    # argument for folder to read
    parser.add_argument("--folder", required=True)
    args = parser.parse_args()

    image_folder_path = pathlib.Path(args.folder)
    logging.info(f"Reading images from folder {image_folder_path} ...")

    # Checkboard dimensions
    CHECKERBOARD = (6, 9)
    subpix_criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.1)
    calibration_flags = (
        cv2.fisheye.CALIB_RECOMPUTE_EXTRINSIC
        + cv2.fisheye.CALIB_CHECK_COND
        + cv2.fisheye.CALIB_FIX_SKEW
    )
    objp = np.zeros((1, CHECKERBOARD[0] * CHECKERBOARD[1], 3), np.float32)
    objp[0, :, :2] = np.mgrid[0 : CHECKERBOARD[0], 0 : CHECKERBOARD[1]].T.reshape(-1, 2)

    objpoints = []  # 3d point in real world space
    imgpoints = []  # 2d points in image plane.

    # iterate through all png/jpg images in image_folder_path
    image_fp_list = list(image_folder_path.glob("*.png")) + list(
        image_folder_path.glob("*.jpg")
    )
    img_info = []
    for fname in image_fp_list:
        logging.info(f"Processing image {fname}")

        img = cv2.imread(fname)
        img_shape = img.shape[:2]

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Find the chess board corners
        ret, corners = cv2.findChessboardCorners(
            gray,
            CHECKERBOARD,
            cv2.CALIB_CB_ADAPTIVE_THRESH
            + cv2.CALIB_CB_FAST_CHECK
            + cv2.CALIB_CB_NORMALIZE_IMAGE,
        )
        # If found, add object points, image points (after refining them)
        if ret:
            objpoints.append(objp)
            cv2.cornerSubPix(gray, corners, (3, 3), (-1, -1), subpix_criteria)
            imgpoints.append(corners)
            img_info.append(
                {
                    "objp": objp,
                    "imgpoints": corners,
                    "img_shape": img_shape,
                    "fname": fname,
                }
            )

    # calculate K & D
    N_imm = len(image_fp_list)  # number of calibration images
    K = np.zeros((3, 3))
    D = np.zeros((4, 1))
    rvecs = [np.zeros((1, 1, 3), dtype=np.float64) for i in range(N_imm)]
    tvecs = [np.zeros((1, 1, 3), dtype=np.float64) for i in range(N_imm)]

    logging.info("Calibration started ...")
    retval, K, D, rvecs, tvecs = cv2.fisheye.calibrate(
        objpoints,
        imgpoints,
        gray.shape[::-1],
        K,
        D,
        rvecs,
        tvecs,
        calibration_flags,
        (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1e-6),
    )

    # # get quality
    # mean_error = []
    # for i in range(len(objpoints)):
    #     imgpoints2, _ = cv2.fisheye.projectPoints(objpoints[i], rvecs[i], tvecs[i], K, D, alpha=0)
    #     error = cv2.norm(imgpoints[i], imgpoints2, cv2.NORM_L2) / len(imgpoints2)
    #     mean_error.append(error)
    # logging.info(f"Total error: {np.mean(mean_error)}")

    # logging.info("Calibration completed and saved to calibration.json")
    # logging.info(f"Camera matrix:\n{K}")
    # logging.info(f"Distortion coefficients:\n{D}")

    # i = img_info[0]
    # img = cv2.imread(str(i["fname"]))
    # # project img_info["objp"] into image
    # imgpoints2, _ = cv2.fisheye.projectPoints(i["objp"], rvecs[0], tvecs[0], K, D)
    # # draw points
    # for p in imgpoints2[0]:
    #     cv2.circle(img, (int(p[0]), int(p[1])), 5, (0, 0, 255), -1)

    # # undistort
    # map1, map2 = cv2.fisheye.initUndistortRectifyMap(K, D, np.eye(3), K, i["img_shape"], cv2.CV_16SC2)
    # undistorted_img = cv2.remap(img, map1, map2, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)

    # cv2.imshow("Original Image", img)
    # cv2.imshow("Undistorted Image", undistorted_img)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()

    # save calibration result
    calibration_data = {
        "mtx": K.tolist(),
        "dist": D.tolist(),
        "rvecs": [rvec.tolist() for rvec in rvecs],
        "tvecs": [tvec.tolist() for tvec in tvecs],
    }

    # extract datetime from calibration_YYYY-MM-DD_HH-MM in data_folder_path dirname or exit with error if not matches
    try:
        calibration_datetime_str = image_folder_path.name.replace("calibration_", "")
        calibration_datetime = datetime.strptime(
            calibration_datetime_str, "%Y-%m-%d_%H-%M"
        )
    except ValueError:
        logging.error(
            f"Folder name {image_folder_path.name} does not match expected format 'calibration_YYYY-MM-DD_HH-MM'"
        )
        sys.exit(1)
    logging.info(f"Extracted datetime: {calibration_datetime}")
    calibration_fp = image_folder_path / (
        "calibration_" + calibration_datetime_str + "_fisheye.json"
    )

    logging.info("Writing calibration data to json file ...")
    with open(str(calibration_fp), "w+") as f:
        json.dump(calibration_data, f, indent=2)

    logging.info("done.")
