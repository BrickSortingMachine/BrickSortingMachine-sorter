import logging
import os
import pathlib
import sys

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
from tools.camera_calibration_process import read_camera_parameters

if __name__ == "__main__":
    # parse command line arguments
    parser = sorter.util.argument_parser.ArgumentParser(
        description="Video capture tool"
    )
    # argument for folder to read
    parser.add_argument("--file", required=True)
    parser.add_argument("--calib", required=True)

    args = parser.parse_args()

    calibration_fp = pathlib.Path(args.calib)
    img_fp = pathlib.Path(args.file)

    # read image
    img = cv2.imread(str(img_fp))

    # get width and height of img
    height, width = img.shape[:2]

    # read the calibration parameters again with method read_camera_parameters for test
    model, K, dist_param = read_camera_parameters(calibration_fp)
    logging.info(f"Read camera matrix:\n{K}")
    logging.info(f"Read distortion coefficients:\n{dist_param}")

    # K_new, _ = cv2.getOptimalNewCameraMatrix(
    #     K, dist_param, (width, height), 1, (width, height)
    # )
    print(K)
    K_new = K.copy()
    K_new[0, 0] *= 0.8
    K_new[1, 1] *= 0.8

    print(K_new)

    # undistort
    if model == "pinhole":
        undistorted_image = cv2.undistort(img, K, dist_param, None, K_new)
    elif model == "fisheye":
        map1, map2 = cv2.fisheye.initUndistortRectifyMap(
            K, dist_param, np.eye(3), K, img.shape[:2], cv2.CV_16SC2
        )
        undistorted_image = cv2.remap(
            img,
            map1,
            map2,
            interpolation=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
        )
    else:
        logging.error(f"Unknown model type {model}")
        sys.exit(1)

    # write
    undist_fp = img_fp.parent / (img_fp.stem + "_undist" + img_fp.suffix)
    cv2.imwrite(str(undist_fp), undistorted_image)
    logging.info(f"Wrote undistorted img to {undist_fp}")

    # show
    cv2.imshow("Original Image", img)
    cv2.imshow("Undistorted Image", undistorted_image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
