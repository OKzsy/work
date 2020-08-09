#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2020/8/3 17:19
# @Author  : zhaoss
# @FileName: test_decorator.py
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


def print_time(func):
    def my_func(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(func.__name__ + " took: %.4f secs." % (end_time - start_time))
        return result

    return my_func


@print_time
def my_fun(val):
    print(val)
    return None


def main():
    my_fun(4)
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
