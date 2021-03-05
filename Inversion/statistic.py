#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2020/12/21 11:32
# @Author  : zhaoss
# @FileName: statistic.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


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


def main(src, color):
    # 获取颜色表
    col_talbe = np.loadtxt(color, dtype=np.float, delimiter=',')
    # 获取带统计影像数据
    src_ds = gdal.Open(src)
    src_data = src_ds.ReadAsArray()
    # 获取影像中不为0像元的总个数和位置索引
    nozero_index = np.where(src_data != 0)
    nozero_count = nozero_index[0].shape[0]
    valid_value = src_data[nozero_index]
    fb = open(color, 'w', newline='')
    for iline in col_talbe:
        slice_min = iline[1]
        slice_max = iline[2]
        slice_index = np.where((valid_value >= slice_min) & (valid_value < slice_max))
        percent = slice_index[0].shape[0] / nozero_count
        line = ','.join([str(int(iline[0])), str(iline[1]), str(iline[2]), str(int(iline[3])), str(int(iline[4])),
                         str(int(iline[5])), str(round(percent, 3))]) + '\n'
        fb.write(line)
    fb.close
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
    src_file = r"F:\test\L2A_T50SKE_20201213_NDVI_石桥村.tif"
    color_table = r"F:\test\L2A_T50SKE_20201213.txt"
    main(src_file, color_table)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
