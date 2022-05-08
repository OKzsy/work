#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/5/31 10:39
# @Author  : zhaoss
# @FileName: hist.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import glob
import time
import numpy as np
import matplotlib.pyplot as plt
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def histogram(data):
    # 获取图像中灰度级范围
    bins = np.arange(start=0, stop=int(data.max()) + 2, step=1)
    n, xbin = np.histogram(data, bins=bins)
    return n, xbin[:-1]


def main(image):
    # 打开影像
    dataset = gdal.Open(image)
    image_data = dataset.ReadAsArray()
    his, bins = histogram(image_data)
    # 绘制直方图
    plt.figure(num=3)
    # plt.plot(bins, his, color='r', marker='o', linestyle='')
    plt.plot(bins, his, "r-")
    plt.show()
    return None


if __name__ == '__main__':
    start_time = time.time()
    # 支持中文路径
    gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
    # 注册所有gdal驱动
    gdal.AllRegister()
    pic_path = r"F:\test_data\DIP3E_out\Fig0940(a).tif"
    main(image=pic_path)
    end_time = time.time()

    print("time: %.4f secs." % (end_time - start_time))
