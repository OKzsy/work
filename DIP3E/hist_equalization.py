#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/5/31 15:28
# @Author  : zhaoss
# @FileName: hist_equalization.py
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
    return n[:], xbin[:-1]


def Cumulative_histogram(data):
    # 获取图像中灰度级范围
    bins = np.arange(start=0, stop=int(data.max()) + 2, step=1)
    n, xbin = np.histogram(data, bins=bins)
    # 计算累计直方图
    cdf = np.cumsum(n) / (data.shape[0] * data.shape[1])
    return cdf[:], xbin[:-1]


def main(image):
    # 打开影像
    dataset = gdal.Open(image)
    image_data = dataset.GetRasterBand(2).ReadAsArray()
    cdf, bins = Cumulative_histogram(image_data)
    # 生成每个像元对应的累积概率密度值
    img_cdf_array = np.zeros_like(image_data, dtype=np.float16)
    for ivalue in bins:
        index = np.where(image_data == ivalue)
        img_cdf_array[index] = cdf[ivalue]
    # 计算直方图
    pdf1, bin1 = histogram(image_data)
    # 绘制直方图
    plt.figure()
    # plt.plot(bins, his, color='r', marker='o', linestyle='')
    plt.plot(bin1, pdf1, "r-")
    plt.show()
    # 生成直方图均衡后的影像
    eq_img = np.round(image_data.max() * img_cdf_array)
    # 计算直方图
    # cdf, bin = Cumulative_histogram(eq_img)
    pdf2, bin2 = histogram(eq_img)
    # # 绘制直方图
    plt.figure()
    # plt.plot(bins, his, color='r', marker='o', linestyle='')
    plt.plot(bin2, pdf2, "k-")
    plt.show()
    # 写出影像
    # out_path = r"F:\文档\数字图像处理第三版\DIP3E_CH03_Original_Images\DIP3E_Original_Images_CH03\test\teat1.tif"
    # driver = gdal.GetDriverByName('GTiff')
    # out_ds = driver.CreateCopy(out_path, dataset, strict=1)
    # out_ds.GetRasterBand(1).WriteArray(eq_img)
    # out_ds.FlushCache()
    return None


if __name__ == '__main__':
    start_time = time.clock()
    # 支持中文路径
    gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
    # 注册所有gdal驱动
    gdal.AllRegister()
    pic_path = r"F:\test_data\数字图像处理标准测试图\4.1.05.tiff"
    main(image=pic_path)
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
