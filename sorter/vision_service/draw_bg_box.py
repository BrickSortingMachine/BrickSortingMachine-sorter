import cv2
import numpy as np


def draw_bg_box(frame_viz, x, y, w, h, alpha=0.5):
    # rectangle dims

    # cut image content
    sub_img = frame_viz[y : y + h, x : x + w]

    # black overlay
    black_rect = np.zeros(sub_img.shape, dtype=np.uint8)

    # blend
    res = cv2.addWeighted(sub_img, 1.0 - alpha, black_rect, alpha, 1.0)

    # but cutout back
    frame_viz[y : y + h, x : x + w] = res
