#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2020/10/9 15:29
# @Author  : zhaoss
# @FileName: Inv_lai.py
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


def main(src, dst):
    # 打开原始影像
    src_ds = gdal.Open(src)
    src_geo = src_ds.GetGeoTransform()
    src_prj = src_ds.GetProjection()
    src_xsize = src_ds.RasterXSize
    src_ysize = src_ds.RasterYSize
    # 获取计算LAI用的波段
    b_6_740 = src_ds.GetRasterBand(5).ReadAsArray() / 10000
    b_7_783 = src_ds.GetRasterBand(6).ReadAsArray() / 10000
    b_8a_865 = src_ds.GetRasterBand(7).ReadAsArray() / 10000
    ttvi = 0.5 * ((865 - 740) * (b_7_783 - b_6_740) - (b_8a_865 - b_6_740) * (783 - 740))
    # 创建输出文件
    drv = gdal.GetDriverByName('GTiff')
    dst_ds = drv.Create(dst, src_xsize, src_ysize, 1, gdal.GDT_Float32)
    dst_ds.SetGeoTransform(src_geo)
    dst_ds.SetProjection(src_prj)
    dst_ds.GetRasterBand(1).WriteArray(ttvi, callback=progress)
    dst_ds.FlushCache()
    src_ds = dst_ds = None
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
    src_file = r'\\192.168.0.234\nydsj\user\ZSS\2020qixian\retrieval\L2A_T50SKE_A018262_20200904T031747_ref_10m.tif'
    dst_file = r'\\192.168.0.234\nydsj\user\ZSS\2020qixian\retrieval\L2A_T50SKE_A018262_20200904T031747_lai_10m.tif'
    main(src_file, dst_file)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))


