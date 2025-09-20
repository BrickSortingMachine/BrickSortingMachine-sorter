import logging
import os
import pathlib
import sys

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
import sorter.util.camera
from tools.camera_calibration_process import read_camera_parameters

if __name__ == "__main__":
    # parse command line arguments
    parser = sorter.util.argument_parser.ArgumentParser(
        description="Video capture tool"
    )
    # argument for folder to read
    parser.add_argument("--file", required=True)
    parser.add_argument("--distort", action="store_true")
    parser.add_argument("--vis", action="store_true")
    args = parser.parse_args()

    img_fp = pathlib.Path(args.file)

    # read image
    img = cv2.imread(str(img_fp))

    # get width and height of img
    height, width = img.shape[:2]

    # read the calibration parameters again with method read_camera_parameters for test
    calibration_fp = (
        pathlib.Path(__file__).parents[1]
        / "calibration"
        / "calibration_2025-09-18_22-27_fisheye.json"
    )
    model, K, dist_param = read_camera_parameters(calibration_fp)

    if not args.distort:
        output_image = sorter.util.camera.undistort_image(img, model, K, dist_param)
        suffix = "_undistorted"

    elif args.distort:
        output_image = sorter.util.camera.distort_image(img, model, K, dist_param)
        suffix = "_distorted"

    # write
    dist_fp = img_fp.parent / (img_fp.stem + suffix + img_fp.suffix)
    if dist_fp.exists():
        logging.error(f"File {dist_fp} already exists")
        sys.exit(1)

    cv2.imwrite(str(dist_fp), output_image)
    logging.info(f"Wrote re-distorted image to {dist_fp}")

    if args.vis:
        cv2.imshow("Original Image", img)
        cv2.imshow("Output Image", output_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
