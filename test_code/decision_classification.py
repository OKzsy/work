#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/10/10 15:49
# @Author  : zhaoss
# @FileName: decision_classification.py
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


def main(infile, outfile):
    # open
    src_ds = gdal.Open(infile)
    xsize = src_ds.RasterXSize
    ysize = src_ds.RasterYSize
    rpj = src_ds.GetProjection()
    geo = src_ds.GetGeoTransform()

    # band1 = src_ds.GetRasterBand(1).ReadAsArray()
    # band2 = src_ds.GetRasterBand(2).ReadAsArray()
    band3 = src_ds.GetRasterBand(3).ReadAsArray()
    band4 = src_ds.GetRasterBand(4).ReadAsArray()
    # band5 = src_ds.GetRasterBand(5).ReadAsArray()
    band6 = src_ds.GetRasterBand(6).ReadAsArray()
    # band7 = src_ds.GetRasterBand(7).ReadAsArray()
    # rendvi = (band6 - band3) / (band6 + band3)
    redvi = band6 - band3
    out_band = np.zeros_like(band3, dtype=np.ubyte) + 200
    ind = np.where((redvi >= 4600) & (redvi <= 6200) & (band4 > 1000))
    out_band[ind] = 12
    driver = gdal.GetDriverByName("GTiff")
    out_ds = driver.Create(outfile, xsize, ysize, 1, gdal.GDT_Byte)
    out_ds.SetProjection(rpj)
    out_ds.SetGeoTransform(geo)
    out_ds.GetRasterBand(1).WriteArray(out_band, callback=progress)
    out_ds = None
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
    in_file = r"\\192.168.0.234\nydsj\user\ZSS\农保项目\S2\62xianque_out\res\L2A_T50SKC_A021665_20190816T031414_ref_10m-prj.tif"
    out_file = r"F:\test_data\L2A_T50SKC_4.tif"
    end_time = time.clock()
    main(in_file, out_file)
    print("time: %.4f secs." % (end_time - start_time))
