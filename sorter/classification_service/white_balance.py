import cv2
import numpy as np


def white_balance(img, random_whitebalance=False):
    top_left = (206, 350)
    bottom_right = (1100, 700)

    img_LAB = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)

    # measure color temperature in measurement area
    measure_cutout = img_LAB[
        top_left[1] : bottom_right[1], top_left[0] : bottom_right[0], :
    ]
    avg_a = np.average(measure_cutout[:, :, 1])
    avg_b = np.average(measure_cutout[:, :, 2])
    # print(f'avg_a: {avg_a} avg_b: {avg_b}')

    if random_whitebalance:
        factor = np.random.randn(1)[0] * 15
    else:
        factor = 0.0

    img_LAB[:, :, 1] = (
        img_LAB[:, :, 1]
        - ((avg_a - 128) * (img_LAB[:, :, 0] / 255.0) * 1.0)
        + ((img_LAB[:, :, 0] / 255.0) * factor)
    )
    img_LAB[:, :, 2] = (
        img_LAB[:, :, 2]
        - ((avg_b - 128) * (img_LAB[:, :, 0] / 255.0) * 1.0)
        + ((img_LAB[:, :, 0] / 255.0) * factor)
    )

    # measure color temperature in measurement area
    measure_cutout = img_LAB[
        top_left[1] : bottom_right[1], top_left[0] : bottom_right[0], :
    ]
    avg_a = np.average(measure_cutout[:, :, 1])
    avg_b = np.average(measure_cutout[:, :, 2])
    # print(f'avg_a: {avg_a} avg_b: {avg_b}')

    img_whitebalanced = cv2.cvtColor(img_LAB, cv2.COLOR_LAB2BGR)

    # cv2.imshow('dfsdf', img_whitebalanced)
    # cv2.waitKey(0)

    return img_whitebalanced
