#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/9/18 10:00
# @Author  : zhaoss
# @FileName: cloud_fraction.py
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


def searchfiles(dirpath, partfileinfo='*', recursive=False):
    """列出符合条件的文件（包含路径），默认不进行递归查询，当recursive为True时同时查询子文件夹"""
    # 定义结果输出列表
    filelist = []
    # 列出根目录下包含文件夹在内的所有文件目录
    pathlist = glob.glob(os.path.join(os.path.sep, dirpath, "*"))
    # 逐文件进行判断
    for mpath in pathlist:
        if os.path.isdir(mpath):
            # 默认不判断子文件夹
            if recursive:
                filelist += searchfiles(mpath, partfileinfo, recursive)
        elif fnmatch.fnmatch(os.path.basename(mpath), partfileinfo):
            filelist.append(mpath)
        # 如果mpath为子文件夹，则进行递归调用，判断子文件夹下的文件

    return filelist


def main(in_path, txt):
    files = searchfiles(in_path, partfileinfo='*.tif')
    fj = open(txt, 'w')
    for file in files:
        basename = os.path.splitext(os.path.basename(file))[0]
        cld_ds = gdal.Open(file)
        cld_array = cld_ds.ReadAsArray()
        no_zerocount = np.where(cld_array != 0)[0].shape[0]
        cld_count = np.where(cld_array == 3)[0].shape[0]
        fraction = round(cld_count / no_zerocount, 3)
        fj.write('{}   {:<}\n'.format(basename, fraction))
        cld_ds = None
    fj.close()
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
    start_time = time.clock()
    in_dir = r"F:\test_data\henan_cld\henan_cld"
    fraction_txt = r"F:\test_data\henan_cld\one_day.txt"
    end_time = time.clock()
    main(in_dir, fraction_txt)
    print("time: %.4f secs." % (end_time - start_time))
