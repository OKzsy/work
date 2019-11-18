#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/8/8 11:36
# @Author  : zhaoss
# @FileName: statistics_area.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
    对输入的分类结果进行分标签面积统计，返回结果为各个种类对应的亩数。

Parameters


"""

import os
import glob
import time
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def main(in_file):
    class_ds = gdal.Open(in_file)
    class_array = class_ds.ReadAsArray()
    rpj = class_ds.GetProjection()
    geo = class_ds.GetGeoTransform()
    osrc = osr.SpatialReference()
    osrc.ImportFromWkt(rpj)
    if osrc.GetAttrValue("UNIT") == "metre":
        area_factor = geo[1] * abs(geo[5])
    else:
        area_factor = geo[1] * 10 ** 5 * abs(geo[5]) * 10 ** 5
    flags = list(np.unique(class_array))
    flags.sort()
    area_dic = {}
    if flags[-1] == 200:
        for iflag in range(len(flags) - 1):
            flag = flags[iflag]
            flag_num = np.where(class_array == flag)[0].shape[0]
            area = flag_num * area_factor / 666.7
            area_dic[flag] = area
    else:
        for iflag in range(1, len(flags)):
            flag = flags[iflag]
            flag_num = np.where(class_array == flag)[0].shape[0]
            area = flag_num * area_factor / 666.7
            area_dic[flag] = area
    print(area_dic)
    return None


if __name__ == '__main__':
    # 支持中文路径
    gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
    # 注册所有gdal驱动
    gdal.AllRegister()
    start_time = time.time()
    class_file = r"\\192.168.0.234\nydsj\user\LT\project\zhiyan\classify\L1A1021435341_1_class.tif"
    end_time = time.time()
    main(in_file=class_file)
    print("time: %.4f secs." % (end_time - start_time))
