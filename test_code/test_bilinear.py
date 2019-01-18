#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import glob
import numpy as np
import time


def bilinear_interpolation(img, out_dim):
    channel, src_h, src_w = img.shape
    dst_h, dst_w = out_dim[1], out_dim[0]
    if src_h == dst_h and src_w == dst_w:
        return img.copy()
    dst_img = np.zeros((3, dst_h, dst_w), dtype=np.uint8)
    scale_x, scale_y = float(src_w) / dst_w, float(src_h) / dst_h
    for i in range(3):
        for dst_y in range(dst_h):
            for dst_x in range(dst_w):
                # find the origin x and y coordinates of dst image x and y
                # use geometric center symmetry
                # if use direct way, src_x = dst_x * scale_x
                src_x = (dst_x + 0.5) * scale_x - 0.5
                src_y = (dst_y + 0.5) * scale_y - 0.5

                # find the coordinates of the points which will be used to compute the interpolation
                src_x0 = int(np.floor(src_x))
                src_x1 = min(src_x0 + 1, src_w - 1)
                src_y0 = int(np.floor(src_y))
                src_y1 = min(src_y0 + 1, src_h - 1)

                # calculate the interpolation
                temp0 = (src_x1 - src_x) * img[i, src_y0, src_x0] + (src_x - src_x0) * img[i, src_y0, src_x1]
                temp1 = (src_x1 - src_x) * img[i, src_y1, src_x0] + (src_x - src_x0) * img[i, src_y1, src_x1]
                dst_img[i, dst_y, dst_x] = int((src_y1 - src_y) * temp0 + (src_y - src_y0) * temp1)

    return dst_img


if __name__ == '__main__':
    start_time = time.clock()
    img = np.arange(108).reshape(3, 6, 6)
    start = time.time()
    dst = bilinear_interpolation(img, (3, 3))

    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
