import logging

import cv2
import numpy as np


def distort_image(img, model, K, dist_param):
    """
    Distorts an image given camera parameters.
    Args:
        img (numpy.ndarray): The input image (assumed to be undistorted).
        model (str): The camera model ("pinhole" or "fisheye").
        K (numpy.ndarray): The camera matrix (intrinsic parameters).
        dist_param (numpy.ndarray): The distortion coefficients.
    Returns:
        numpy.ndarray: The distorted image.
    """
    height, width = img.shape[:2]
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
        raise Exception(f"Unknown model type {model}")

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

    return distorted_image
