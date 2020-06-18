#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2020/06/18 20:57
# @Author  : zhaoss
# @FileName: sig.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


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

def sig(x):
    '''
    Sigmoid函数
    :param x:
    :return:
    '''
    return 1 / (1 + np.exp(-x))
def main():
    feature = np.arange(10)
    res = sig(feature)
    print(res)
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

    main()
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))

