#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/6/3 16:21
# @Author  : zhaoss
# @FileName: hist_match.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import glob
import gc
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
    return n[:], xbin[:-1]


def img_stretch(ori_image_data, std_img):
    ori_min = ori_image_data.min()
    ori_max = ori_image_data.max()
    std_min = std_img.min()
    std_max = std_img.max()
    stretch_ori = std_min + (std_max - std_min) * ((ori_image_data - ori_min) / (ori_max - ori_min))
    return stretch_ori.astype(np.uint16)


def histogram_equalization(data):
    # 获取图像中灰度级范围
    bins = np.arange(start=1, stop=int(data.max()) + 2, step=1)
    n, xbin = np.histogram(data, bins=bins)
    zero_index = np.where(data == 0)
    # 计算累计直方图
    cdf = np.cumsum(n) / (data.shape[0] * data.shape[1] - zero_index[0].shape[0])
    return cdf[:], xbin[:-1]


def match(ori_image_data, std_img):
    ori_image_data = img_stretch(ori_image_data, std_img)
    ori_cdf, ori_bins = histogram_equalization(ori_image_data)
    # 打开标准影像进行直方图均衡
    std_cdf, std_bins = histogram_equalization(std_img)
    std_img = None
    img_eq_array = np.zeros_like(ori_image_data, dtype=np.uint16)
    # 处理原始影像
    for ivalue in ori_bins:
        # 计算原始和标准之间的差异
        diff = np.abs(ori_cdf[ivalue - 1] - std_cdf)
        index = np.where(diff == diff.min())
        res_index = np.where(ori_image_data == ivalue)
        img_eq_array[res_index] = index[0][0]
        print("ivalue: {}, new_value: {}".format(ivalue, index[0][0]))
    ori_image_data = None
    gc.collect()
    return img_eq_array


def main(image, stand_img):
    ori_ds = gdal.Open(image)
    std_ds = gdal.Open(stand_img)
    bandcount = ori_ds.RasterCount
    # 写出影像
    out_path = r"F:\ChangeMonitoring\sample\test\img_out\test4.tiff"
    driver = gdal.GetDriverByName('GTiff')
    out_ds = driver.CreateCopy(out_path, ori_ds, strict=1)
    for iband in range(bandcount):
        img_arr = ori_ds.GetRasterBand(iband + 1).ReadAsArray()
        std_arr = std_ds.GetRasterBand(iband + 1).ReadAsArray()
        eq_arr = match(img_arr, std_arr)
        out_ds.GetRasterBand(iband + 1).WriteArray(eq_arr)
    out_ds.FlushCache()
    return None


if __name__ == '__main__':
    start_time = time.clock()
    # 支持中文路径
    gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
    # 注册所有gdal驱动
    gdal.AllRegister()
    ori_pic_path = r"F:\ChangeMonitoring\sample\test\img_out\GF2_2985952_000000.tiff"
    stand_pic_path = r"F:\ChangeMonitoring\sample\test\img_out\GF2_2985952_000002.tiff"
    main(stand_img=stand_pic_path, image=ori_pic_path)
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
