#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2022/05/09 17:50
# @Author  : zhaoss
# @FileName: top_transform.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
白顶帽变换，即原图减去其开操作，用于暗背景上的亮物体
Parameters

"""
import os
import sys
import glob
import time
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
    extended_val = np.pad(matrix, ((ys_fill, ys_fill), (xs_fill, xs_fill)),
                          'constant', constant_values=default_value)
    # extended_val = np.pad(matrix, ((ys_fill, ys_fill), (xs_fill, xs_fill)), 'reflect')
    matrix = None
    return extended_val


def gray_filtering(xs, ys, ori_xsize, ori_ysize, ext_img):
    """

    :param xs: 卷积核大小：列
    :param ys: 卷积核大小：行
    :param kernel: 卷积核
    :param ext_img: 经扩展后的影像
    :return: 滤波后的影像
    """
    # 使用切片后影像的波段数
    # 创建切片后存储矩阵
    channel = xs * ys
    filtered_img = np.zeros((channel, ori_ysize, ori_xsize), dtype=np.uint8)
    ichannel = 0
    for irow in range(ys):
        for icol in range(xs):
            filtered_img[ichannel, :, :] = ext_img[irow: irow +
                                                   ori_ysize, icol: icol + ori_xsize]
            ichannel += 1
    return filtered_img[:, :, :]


def gray_erode(win_size, src_data):
    ysize, xsize = src_data.shape
    extend_src_data = Extend(win_size, win_size, src_data, default_value=255)
    filter_img = gray_filtering(int(win_size), int(
        win_size), xsize, ysize, extend_src_data)
    dst_img = np.min(filter_img, axis=0)
    filter_img = None
    return dst_img


def gray_dilate(win_size, src_data):
    ysize, xsize = src_data.shape
    extend_src_data = Extend(win_size, win_size, src_data, default_value=0)
    filter_img = gray_filtering(int(win_size), int(
        win_size), xsize, ysize, extend_src_data)
    dst_img = np.max(filter_img, axis=0)
    filter_img = None
    return dst_img


def opening(win_size, thr, src_data):
    """
    先腐蚀后膨胀，光滑目标轮廓，消除小目标（如去掉毛刺和孤立点），在纤细出分离物体，常用于去除小颗粒噪声以及断开目标之间的粘连
    :param win_size:
    :param src_data:
    :return:
    """
    for _ in range(thr):
        src_data = gray_erode(win_size, src_data)
    for _ in range(thr):
        src_data = gray_dilate(win_size, src_data)
    return src_data


def closing(win_size, thr, src_data):
    """
    先膨胀后腐蚀，能够填平小湖（即小孔），弥合小裂缝，而总的位置和形状不变
    :param win_size:
    :param src_data:
    :return:
    """
    for _ in range(thr):
        src_data = gray_dilate(win_size, src_data)
    for _ in range(thr):
        src_data = gray_erode(win_size, src_data)
    return src_data


def main(src, dst, op, size):
    # 打开影像
    src_ds = gdal.Open(src)
    prj = src_ds.GetProjection()
    geo = src_ds.GetGeoTransform()
    src_data = src_ds.GetRasterBand(1).ReadAsArray()
    src_data = np.pad(src_data, ((1, 1), (1, 1)), 'constant', constant_values=30)
    xsize = src_data.shape[1]
    ysize = src_data.shape[0]
    # 进行变换
    if op:
        filter_img = closing(size, 1, src_data)
        transf_img = filter_img - src_data
    else:
        filter_img = opening(size, 1, src_data)
        transf_img = src_data - filter_img
    # 对穗帽变换后的影像进行开运算，去除零星噪声点
    transf_img = opening(5, 3, transf_img)
    # 创建输出文件
    drv = gdal.GetDriverByName('GTiff')
    dst_ds = drv.Create(dst, xsize, ysize, 1, gdal.GDT_Byte)
    dst_ds.SetProjection(prj)
    dst_ds.SetGeoTransform(geo)
    dstband = dst_ds.GetRasterBand(1)
    dstband.WriteArray(transf_img)
    dstband.FlushCache()
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
    in_dir = r"F:\test_data\DIP3E_out\Fig0940(a).tif"
    out_dir = r"F:\test_data\DIP3E_out\Fig0940(a)_top2.tif"
    # 选择进行的形态学运算top_hat=0, bottom=1
    operate = 0
    # 结构元大小（即窗口大小-SE size)
    se_size = 31
    main(in_dir, out_dir, operate, se_size)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
