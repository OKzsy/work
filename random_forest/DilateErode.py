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


def Extend(xs, ys, matrix, default_value):
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
    extended_val = np.pad(matrix, ((ys_fill, ys_fill), (xs_fill, xs_fill)), 'constant', constant_values=default_value)
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


def opening(win_size, kernel, fr_value, bg_value, src_data):
    """
    先腐蚀后膨胀，光滑目标轮廓，消除小目标（如去掉毛刺和孤立点），在纤细出分离物体，常用于去除小颗粒噪声以及断开目标之间的粘连
    :param win_size:
    :param kernel:
    :param fr_value:
    :param bg_value:
    :param src_data:
    :return:
    """
    filter_img = Erode(win_size, kernel, fr_value, bg_value, src_data)
    filter_img = Dilate(win_size, kernel, fr_value, bg_value, filter_img)
    return filter_img


def closing(win_size, kernel, fr_value, bg_value, src_data):
    """
    先膨胀后腐蚀，填充凹陷，弥合孔洞和裂缝，常用来填充空洞，凹陷和连接断开的目标，也具有一定平滑边缘的效果
    :param win_size:
    :param kernel:
    :param fr_value:
    :param bg_value:
    :param src_data:
    :return:
    """
    filter_img = Dilate(win_size, kernel, fr_value, bg_value, src_data)
    filter_img = Erode(win_size, kernel, fr_value, bg_value, filter_img)
    return filter_img


def Dilate(win_size, kernel, fr_value, bg_value, src_data):
    """
    对原图像进行膨胀
    :param win_size:
    :param kernel:
    :param fr_value:
    :param bg_value:
    :param src_data:
    :return:
    """
    ysize, xsize = src_data.shape
    extend_src_data = Extend(win_size, win_size, src_data, default_value=0)
    filter_img = img_filtering(int(win_size), int(win_size), xsize, ysize, kernel, extend_src_data)
    filter_img = np.where(filter_img == int(connect + 1) * bg_value, src_data, fr_value)
    extend_src_data = None
    return filter_img


def Erode(win_size, kernel, fr_value, bg_value, src_data):
    """
    对原图像进行腐蚀
    :param win_size:
    :param kernel:
    :param fr_value:
    :param bg_value:
    :param src_data:
    :return:
    """
    ysize, xsize = src_data.shape
    extend_src_data = Extend(win_size, win_size, src_data, default_value=255)
    filter_img = img_filtering(int(win_size), int(win_size), xsize, ysize, kernel, extend_src_data)
    filter_img = np.where(filter_img == int(connect + 1) * fr_value, src_data, bg_value)
    extend_src_data = None
    return filter_img


def gray_filtering(xs, ys, ori_xsize, ori_ysize, kernel, ext_img):
    """

    :param xs: 卷积核大小：列
    :param ys: 卷积核大小：行
    :param kernel: 卷积核
    :param ext_img: 经扩展后的影像
    :return: 滤波后的影像
    """
    # 使用切片后影像的波段书
    # 创建切片后存储矩阵
    index = np.where(kernel == 1)
    channel = kernel.size
    filtered_img = np.zeros((channel, ori_ysize, ori_xsize), dtype=np.uint8)
    ichannel = 0
    for irow in range(ys):
        for icol in range(xs):
            filtered_img[ichannel, :, :] = ext_img[irow: irow + ori_ysize, icol: icol + ori_xsize]
            ichannel += 1
    return filtered_img[index[0], :, :]


def gray_erode(win_size, kernel, src_data):
    ysize, xsize = src_data.shape
    extend_src_data = Extend(win_size, win_size, src_data, default_value=255)
    filter_img = gray_filtering(int(win_size), int(win_size), xsize, ysize, kernel, extend_src_data)
    dst_img = np.min(filter_img, axis=0)
    filter_img = None
    return dst_img


def gray_dilate(win_size, kernel, src_data):
    ysize, xsize = src_data.shape
    extend_src_data = Extend(win_size, win_size, src_data, default_value=0)
    filter_img = gray_filtering(int(win_size), int(win_size), xsize, ysize, kernel, extend_src_data)
    dst_img = np.max(filter_img, axis=0)
    filter_img = None
    return dst_img


def main(src, dst, connect):
    # 定义结构元
    SE = {4: np.array([0, 1, 0, 1, 1, 1, 0, 1, 0]),
          8: np.array([1, 1, 1, 1, 1, 1, 1, 1, 1])}
    # 前景值
    fr_value = 1
    # 背景值
    bg_value = 0
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
    filter_img = gray_dilate(win_size, kernel, src_data)
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
    connect = 4
    # 学习linux命令行替代工具
    src_file = r"F:\test_data\dengfeng\class\test.tif"
    dst_file = r"F:\test_data\dengfeng\class\test_gray_dilate.tif"
    main(src_file, dst_file, connect)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
