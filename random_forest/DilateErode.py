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


def main():
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
    src_file = r""
    dst_file = r""
    main(src_file, dst_file, connect)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))

