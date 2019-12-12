#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/12/3 10:58
# @Author  : zhaoss
# @FileName: gaussian_pyr.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import sys
import glob
import gc
import math
import time
import fnmatch
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def resize(src_dst, dst_xsize, dst_ysize, seq):
    """
    根据输入的目标影像行列数对原始影像进行缩放，缩放方法为双线性插值
    :param src_dst: 原始数据集
    :param dst_xsize: 目标影像列数
    :param dst_ysize: 目标影像行数
    :return: 返回重采样后的目标影像数据集
    """
    # 获取原始影像的数据类型
    datatype = src_dst.GetRasterBand(1).DataType
    # 根据目标大小，在内存创建结果影像
    tmp_dst_path = r'/vsimem/tmp_dst_{}.tiff'.format(str(seq))
    gdal.Translate(tmp_dst_path, src_dst, resampleAlg=gdal.GRA_Bilinear, format='GTiff', width=dst_xsize,
                   height=dst_ysize, outputType=datatype)
    tmp_dst = gdal.Open(tmp_dst_path)
    src_dst = None
    gdal.Unlink(tmp_dst_path)
    gc.collect()
    return tmp_dst


def pyramid(octave_val, src_dst, points, n=0):
    if n == octave_val:  # 当达到指定层数后，返回监测的极值点
        # 返回极值点，可是设定在该返回位置做最后一层
        return points
    else:
        if n == 0:
            # 获取原始数据集的基本信息
            src_xsize = src_dst.RasterXSize
            src_ysize = src_dst.RasterYSize
            new_dst = resize(src_dst, src_xsize * 2, src_ysize * 2, n)  # 放大一倍
            print("cols:", new_dst.RasterXSize)
            src_dst = None
            # 监测极值点，包括极值点定位
            # points.append(list(range(int(dataset))))
            return pyramid(octave_val, new_dst, points[:], n + 1)
        else:
            # 获取原始数据集的基本信息
            src_xsize = src_dst.RasterXSize
            src_ysize = src_dst.RasterYSize
            new_dst = resize(src_dst, int(src_xsize / 2), int(src_ysize / 2), n)  # 放大一倍
            print("cols:", new_dst.RasterXSize)
            src_dst = None
            # 监测极值点，包括极值点定位
            # points.append(list(range(int(dataset))))
            return pyramid(octave_val, new_dst, points[:], n + 1)


def main(in_fn, band_index):
    # 读取影像
    src_dst = gdal.Open(in_fn)
    xsize = src_dst.RasterXSize
    ysize = src_dst.RasterYSize
    ori_band = src_dst.GetRasterBand(band_index)
    dtype = ori_band.DataType
    # 提取单波段为一个数据集进行高斯尺度金字塔构建
    driver = gdal.GetDriverByName('MEM')
    src_one_dst = driver.Create('', xsize, ysize, 1, dtype)
    src_one_dst.GetRasterBand(1).WriteArray(ori_band.ReadAsArray())
    src_dst = ori_band = None
    # 确定高斯金子塔的组数
    octave = math.floor(math.log(min(xsize, ysize), 2) / 2)
    # if octave > 5:
    #     octave = 5
    octave = 15
    # 构建高斯金字塔并检测极值点
    extreme_points = []
    extreme_points = pyramid(octave, src_one_dst, extreme_points[:])
    # num = 0
    # o = 4
    # dataset = 10
    # res_points = []
    # res = pyramid(num, o, dataset, res_points[:])
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
    in_file = r"F:\SIFT\left.PNG"
    in_file = r"F:\test_data\new_test\GF2_20180718_L1A0003330812_sha.tiff"
    band_idx = 1
    main(in_file, band_idx)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
