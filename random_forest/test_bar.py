#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2020/6/12 16:35
# @Author  : zhaoss
# @FileName: test_bar.py
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
import multiprocessing as mp
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def pickle_process(num):
    """thread worker function"""
    print('Worker:', num, flush=True)
    time.sleep(1)
    return 1


class Bar():
    """用于多线程显示进度条"""
    members = 0

    def __init__(self, num, total):
        Bar.members += num
        progress(Bar.members / total)




def main():
    pool = mp.Pool(5)
    total = 10
    update = lambda args: Bar(args, total)
    for i in range(10):
        pool.apply_async(pickle_process, args=(i,), callback=update)  # 通过callback来更新进度条
    pool.close()
    pool.join()
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
