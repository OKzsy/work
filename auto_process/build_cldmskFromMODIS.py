#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/9/17 13:39
# @Author  : zhaoss
# @FileName: build_cldmskFromMODIS.py
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


def s2e(s):
    """

    :param s: 原始cldMSK十进制的值
    :return: 经解析后判断是否为云的cld_code
             1:该像元由于种种原因不能判断
             2:晴朗像元
             3:云像元
    """
    cld_code = -10
    if s == 0:
        cld_code = 0
        return cld_code
    if s < 0:
        s = s * -1 - 1
        e = [0, 0, 0, 0, 0, 0, 0, 0]
        for i in range(0, 8, 1):
            e[i] = int(s % 2)
            s = s // 2
        bin_value = [str(1 - x) for x in list(reversed(e))]
    else:
        e = [0, 0, 0, 0, 0, 0, 0, 0]
        for i in range(0, 8, 1):
            e[i] = int(s % 2)
            s = s // 2
        bin_value = [str(x) for x in list(reversed(e))]
    determined = bin_value[-1:][0]
    binary_value = ''.join(bin_value)
    bit_value = binary_value[-3:-1]
    if determined == 0:
        cld_code = 1
    elif bit_value == '00':
        cld_code = 3
    elif bit_value == '01':
        cld_code = 2
    elif bit_value == '10':
        cld_code = 2
    else:
        cld_code = 2
    return cld_code


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


def main(in_path, out_path):
    # 搜索所有待处理影像
    files = searchfiles(in_path, partfileinfo='*.tif')
    for in_file in files:
        basename = os.path.basename(in_file)
        # 打开原始cldMSK
        cldMSK_ds = gdal.Open(in_file)
        xsize = cldMSK_ds.RasterXSize
        ysize = cldMSK_ds.RasterYSize
        proj = cldMSK_ds.GetProjection()
        geo = cldMSK_ds.GetGeoTransform()
        cldMSK_array = cldMSK_ds.ReadAsArray()
        unique_value = np.unique(cldMSK_array)
        for value in unique_value:
            code = s2e(value)
            index = np.where(cldMSK_array == value)
            cldMSK_array[index] = code
        driver = gdal.GetDriverByName('GTiff')
        out_file = os.path.join(out_path, basename)
        out_ds = driver.Create(out_file, xsize, ysize, 1, gdal.GDT_Byte)
        out_ds.SetProjection(proj)
        out_ds.SetGeoTransform(geo)
        out_ds.GetRasterBand(1).WriteArray(cldMSK_array)
        out_ds = None
        cldMSK_ds = None

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
    in_dir = r"F:\test_data\henan_cld\cld"
    out_dir = r"F:\test_data\henan_cld\cld_mask"
    end_time = time.clock()
    main(in_dir, out_dir)
    print("time: %.4f secs." % (end_time - start_time))
