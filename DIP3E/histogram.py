#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2022/05/08 12:31
# @Author  : zhaoss
# @FileName: histogram.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:

Parameters

"""
import os
import time
import numpy as np
import matplotlib.pyplot as plt
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def stats_hist(img_data, bg_val=0, no_bg=True):
    '''
    统计影像直方图，默认背景值为0，no_bg参数设置最终直方图中考虑不考虑背景值，默认不考虑
    '''
    # 获取影像的最大、最小值
    img_max = img_data.max()
    img_min = img_data.min()
    # 获取图像中灰度级范围的统计直方图
    bins = np.arange(start=img_min, stop=img_max + 2, step=1)
    n, xbin = np.histogram(img_data, bins=bins)
    xbin = xbin[:-1]
    if no_bg:
        xbin_indx = np.where(xbin != bg_val)
        n = n[xbin_indx]
        xbin = xbin[xbin_indx]
    return n, xbin


def main(image):
    # 打开影像
    dataset = gdal.Open(image)
    img_data = dataset.ReadAsArray()
    # img_list = [-1, -1, 0, 1, 1, 2, 2, 2, 2, 3, 3, 3, 5, 5]
    # img_data = np.array(img_list)
    his, bins = stats_hist(img_data)
    # 绘制直方图
    plt.figure(num=3)
    plt.plot(bins, his, "r-")
    plt.show()

    return None


if __name__ == '__main__':
    # 支持中文路径
    gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
    # 支持中文属性字段
    gdal.SetConfigOption("SHAPE_ENCODING", "GBK")
    # 注册所有ogr驱动
    ogr.RegisterAll()
    # 注册所有gdal驱动
    gdal.AllRegister()
    start_time = time.time()
    pic_path = r"F:\test_data\DIP3E_out\Fig0940(a).tif"
    main(pic_path)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
