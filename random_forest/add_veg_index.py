#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2020/5/6 9:34
# @Author  : zhaoss
# @FileName: add_veg_index.py
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


def add_ndvi(red=None, inf=None):
    """
    增加归一化植被指数
    :param red: 红波段
    :param inf: 近红外波段
    :return: 归一化植被指数
    """
    red = red.astype(np.int16)
    inf = inf.astype(np.int16)
    ndvi = (((inf - red) / (inf + red + 0.000001)) * 1000).astype(np.int16)
    red = inf = None
    return ndvi


def main(infile, outfile):
    in_ds = gdal.Open(infile)
    rpj = in_ds.GetProjection()
    geo = in_ds.GetGeoTransform()
    xsize = in_ds.RasterXSize
    ysize = in_ds.RasterYSize
    bandnum = in_ds.RasterCount
    # 获取数据
    oridata = in_ds.ReadAsArray()
    # 增加各种指数
    new_band = 0
    # 归一化植被指数
    ndvi = add_ndvi(red=oridata[2, :, :], inf=oridata[6, :, :])
    new_band += 1
    # 合并所有增加的指数
    index_arr= np.zeros((new_band, ysize, xsize))
    index_arr[0, :, :] = ndvi
    ndvi = None
    # 写出数据
    tiff_driver = gdal.GetDriverByName('GTiff')
    out_ds = tiff_driver.Create(outfile, xsize, ysize, bandnum + new_band, gdal.GDT_Int16)
    out_ds.SetProjection(rpj)
    out_ds.SetGeoTransform(geo)
    # 写原始影像
    for iband in range(bandnum):
        out_ds.GetRasterBand(iband + 1).WriteArray(oridata[iband, :, :])
    for iband in range(new_band):
        out_ds.GetRasterBand(bandnum + iband + 1).WriteArray(index_arr[iband, :, :])
    out_ds.FlushCache()
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
    start_time = time.time()
    infile = r"F:\test_data\dengfeng\S2\L2A_20200318_dengfeng.tif"
    outfile = r"F:\test_data\dengfeng\S2\L2A_20200318_dengfeng_with_veg_index.tif"
    main(infile, outfile)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
