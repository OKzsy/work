#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/11/20 16:27
# @Author  : zhaoss
# @FileName: Gaussian_filter.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
    对输入图像进行拉普拉斯锐化增强
Parameters


"""

import os
import sys
import glob
import time
import math
import fnmatch
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def Extend(xs, ys, matrix):
    """
    根据滤波模板的大小，对原始影像矩阵进行外扩。
    :param xs: 滤波模板的xsize，要求为奇数
    :param ys: 滤波模板的ysize，要求为奇数
    :param matrix: 原始影像矩阵
    :return: 依据模板大小扩展后的矩阵
    """
    extended_xs = (xs - 1) + matrix.shape[1]
    extended_ys = (ys - 1) + matrix.shape[0]
    extended_val = np.zeros((extended_ys, extended_xs), dtype=matrix.dtype)
    xs_start_pos = int((xs - 1) / 2)
    ys_start_pos = int((ys - 1) / 2)
    extended_val[ys_start_pos: -ys_start_pos, xs_start_pos: -xs_start_pos] = matrix
    matrix = None
    return extended_val


def function_template(sigma_val):
    ksize = math.ceil(2 * round(3 * sigma_val) + 1)
    template = np.zeros((ksize, ksize), dtype=np.float32)
    for row in range(ksize):
        for col in range(ksize):
            u = row - ksize // 2
            v = col - ksize // 2
            template[row, col] = math.exp(-(u ** 2 + v ** 2) / (2 * sigma_val ** 2)) / (2 * math.pi * sigma_val ** 2)

    return ksize, template / np.sum(template)


def img_filtering(xs, ys, ori_xsize, ori_ysize, kernel, ext_img):
    """

    :param xs: 卷积核大小：列
    :param ys: 卷积核大小：行
    :param kernel: 卷积核
    :param ext_img: 经扩展后的影像
    :return: 滤波后的影像
    """
    # 使用切片后影像的波段书
    # 创建切片后存储矩阵
    filtered_img = np.zeros((ori_ysize, ori_xsize), dtype=np.float32)
    for iraw in range(ys):
        for icol in range(xs):
            filtered_img += ext_img[iraw: iraw + ori_ysize, icol: icol + ori_xsize] * kernel[iraw, icol]
    ext_img = None
    return filtered_img


def main(in_image, out_image):
    # 打开影像获取数据
    img_dst = gdal.Open(in_image)
    xsize = img_dst.RasterXSize
    ysize = img_dst.RasterYSize
    imgval1 = img_dst.GetRasterBand(1).ReadAsArray()
    # 定义滤波函数
    # kernel = np.array([[1, 1, 1], [1, -8, 1], [1, 1, 1]])
    # kernel_xsize = 3
    # kernel_ysize = 3
    sigma = 0.6
    win_size, template = function_template(sigma)
    kernel_xsize = kernel_ysize = win_size
    # 结合滤波函数对待滤波影像进行边缘扩展，目的是保证滤波结果和原始影像大小一致
    extended_img = Extend(kernel_xsize, kernel_ysize, imgval1)
    # 使用模板进行滤波
    btime = time.time()
    filtered_img = img_filtering(kernel_xsize, kernel_ysize, xsize, ysize, template, extended_img)
    etime = time.time()
    print('time:{}'.format(etime - btime))
    # # 生成锐化结果，并恢复原始图像灰度范围
    # sharpen_img = imgval1 - filtered_img
    # tmp_sharpen_img = imgval1.min() + ((imgval1.max() - imgval1.min()) / (sharpen_img.max() - sharpen_img.min())) * (
    #         sharpen_img - sharpen_img.min())
    # 输出结果
    driver = gdal.GetDriverByName('GTiff')
    out_dst = driver.Create(out_image, xsize, ysize, 1, gdal.GDT_Float32)
    out_dst.GetRasterBand(1).WriteArray(filtered_img)
    out_dst.FlushCache()
    out_dst = None
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
    imgPath = r"F:\test_data\数字图像处理标准测试图\Lena.tif"
    outPath = r"F:\test_data\数字图像处理标准测试图\test_out\Lena_16.0.tif"
    main(imgPath, outPath)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
