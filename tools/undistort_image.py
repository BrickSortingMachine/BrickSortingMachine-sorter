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
    parser.add_argument("--distort", action="store_true")

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

    if not args.distort:
        # undistort
        print(K)
        K_new = K.copy()
        K_new[0, 0] *= 0.7
        K_new[1, 1] *= 0.7

        print(K_new)

        # undistort
        if model == "pinhole":
            undistorted_image = cv2.undistort(img, K, dist_param, None, K_new)
        elif model == "fisheye":
            map1, map2 = cv2.fisheye.initUndistortRectifyMap(
                K,
                dist_param,
                np.eye(3),
                K_new,
                (img.shape[1], img.shape[0]),
                cv2.CV_16SC2,
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

    elif args.distort:
        # -------------------
        # DISTORTION
        # -------------------
        logging.info("Performing distortion...")
        # This block takes a previously undistorted image and applies distortion to it.

        # K_of_distorted_output: The camera matrix of the final, distorted image.
        # This is the original camera matrix from the calibration file.
        K_of_distorted_output = K

        # K_of_undistorted_input: The camera matrix corresponding to the input 'img'.
        # We assume it was generated using the same scaling factor as in the undistortion step.
        K_of_undistorted_input = K.copy()
        scale_factor = 0.7  # MUST match the factor used to create the undistorted image
        K_of_undistorted_input[0, 0] *= scale_factor
        K_of_undistorted_input[1, 1] *= scale_factor

        logging.info(f"Source (undistorted) camera matrix:\n{K_of_undistorted_input}")
        logging.info(f"Target (distorted) camera matrix:\n{K_of_distorted_output}")

        # To distort the image, we create a map from the output (distorted) image
        # coordinates back to the source (undistorted) image coordinates.

        # 1. Create a grid of (x, y) coordinates for every pixel in the target distorted image.
        distorted_coords_x, distorted_coords_y = np.meshgrid(
            np.arange(width), np.arange(height)
        )

        # 2. Format the grid into a (N, 1, 2) array for OpenCV functions.
        distorted_pixel_coords = (
            np.stack([distorted_coords_x, distorted_coords_y], axis=-1)
            .reshape(-1, 1, 2)
            .astype(np.float32)
        )

        # 3. Use `undistortPoints` to find where each distorted pixel would be located in
        #    the source (undistorted) image's coordinate system. The 'P' argument
        #    directly projects the points into pixel coordinates for the camera
        #    defined by K_of_undistorted_input.
        if model == "pinhole":
            # The original code had an incorrect placeholder for this.
            undistorted_pixel_coords = cv2.undistortPoints(
                distorted_pixel_coords,
                K_of_distorted_output,
                dist_param,
                P=K_of_undistorted_input,
            )
        elif model == "fisheye":
            undistorted_pixel_coords = cv2.fisheye.undistortPoints(
                distorted_pixel_coords,
                K_of_distorted_output,
                dist_param,
                P=K_of_undistorted_input,
            )
        else:
            logging.error(f"Unknown model type {model}")
            sys.exit(1)

        # 4. The output is a list of coordinates. Reshape it into two maps (one for x,
        #    one for y) that cv2.remap can use.
        undistorted_pixel_coords = undistorted_pixel_coords.squeeze()
        map1 = undistorted_pixel_coords[:, 0].reshape(height, width).astype(np.float32)
        map2 = undistorted_pixel_coords[:, 1].reshape(height, width).astype(np.float32)

        # 5. Apply the mapping to the source image to get the final distorted image.
        distorted_image = cv2.remap(
            img,
            map1,
            map2,
            interpolation=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
        )

        # write
        dist_fp = img_fp.parent / (img_fp.stem + "_redistorted" + img_fp.suffix)
        cv2.imwrite(str(dist_fp), distorted_image)
        logging.info(f"Wrote re-distorted image to {dist_fp}")

        # show
        cv2.imshow("Original Undistorted Image", img)
        cv2.imshow("Re-distorted Image", distorted_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
