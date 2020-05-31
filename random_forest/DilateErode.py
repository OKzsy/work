#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2020/05/30 22:01
# @Author  : zhaoss
# @FileName: DilateErode.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
用于形态学滤波，包含膨胀，腐蚀，开操作，闭操作

Parameters:


"""

import os
import sys
import glob
import time
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
    xs_fill = int((xs - 1) / 2)
    ys_fill = int((ys - 1) / 2)
    # 使用镜像填充
    extended_val = np.pad(matrix, ((ys_fill, ys_fill), (xs_fill, xs_fill)), 'constant')
    matrix = None
    return extended_val


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
    filtered_img = np.zeros((ori_ysize, ori_xsize), dtype=np.uint8)
    for irow in range(ys):
        for icol in range(xs):
            filtered_img += ext_img[irow: irow + ori_ysize, icol: icol + ori_xsize] * kernel[icol + irow * xs]
    return filtered_img


def main(src, dst, connect):
    # 定义结构元
    SE = {4: np.array([0, 1, 0, 1, 1, 1, 0, 1, 0]),
          8: np.array([1, 1, 1, 1, 1, 1, 1, 1, 1])}
    src_ds = gdal.Open(src)
    xsize = src_ds.RasterXSize
    ysize = src_ds.RasterYSize
    prj = src_ds.GetProjection()
    geo = src_ds.GetGeoTransform()
    src_data = src_ds.ReadAsArray()
    # 创建输出影像
    drv = gdal.GetDriverByName('GTiff')
    dst_ds = drv.Create(dst, xsize, ysize, 1, gdal.GDT_Byte)
    dst_ds.SetProjection(prj)
    dst_ds.SetGeoTransform(geo)
    kernel = SE[connect]
    win_size = np.sqrt(kernel.size)
    if not win_size % 1 == 0:
        raise ('The size of SE is wrong!')
    extend_src_data = Extend(win_size, win_size, src_data)
    filter_img = img_filtering(int(win_size), int(win_size), xsize, ysize, kernel, extend_src_data)
    filter_img = np.where(filter_img == int(connect), 0, filter_img)
    filter_img *= 255
    dst_ds.GetRasterBand(1).WriteArray(filter_img)
    dst_ds = None
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
    connect = 8
    # 学习linux命令行替代工具
    src_file = r"/home/zss/DIP3E_CH09_Original_Images/Fig0905(a)(wirebond-mask).tif"
    dst_file = r"/home/zss/DIP3E_out/Fig0905(a)(wirebond-mask).tif"
    main(src_file, dst_file, connect)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
