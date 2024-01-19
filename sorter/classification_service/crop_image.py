import cv2
import numpy as np

import sorter.classification_service.white_balance


def crop_image(
    input_img, low, random_crop_augmentation=False, random_whitebalance=False
):
    # ensure uncropped original image directly from camera
    assert input_img.shape[0] == 720  # y
    assert input_img.shape[1] == 1280  # x
    assert input_img.shape[2] == 3

    if low:
        x = 330
        y = 250
        w = 400
        h = 400
    else:
        x = 380
        y = 10
        w = 300
        h = 300

    if random_whitebalance:
        input_img = input_img.copy()
        # first normalizing whitebalance takes twice the amount of time and not strictly needed
        # input_img = sorter.white_balance.white_balance(input_img, random_whitebalance=False)  # normalize first
        input_img = sorter.classification_service.white_balance.white_balance(
            input_img, random_whitebalance=True
        )  # then randomize

    if random_crop_augmentation:
        x += int(np.random.randn(1)[0] * 30)
        y += int(np.random.randn(1)[0] * 35)
        y = max(0, y)
        # raise Exception('use uniform distribution instead here')

    output_img = input_img[y : y + h, x : x + w]
    output_img = cv2.resize(output_img, (224, 224), interpolation=cv2.INTER_CUBIC)

    return output_img
