#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2020/12/30 10:13
# @Author  : zhaoss
# @FileName: changelocation.py
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


def main(src, dir, point):
    rasters = searchfiles(src, partfileinfo='*.tif')
    for raster in rasters:
        basename = os.path.splitext(os.path.basename(raster))[0]
        dst_basename = basename + '_bak.tif'
        dst_raster = os.path.join(dir, dst_basename)
        src_raster_ds = gdal.Open(raster)
        xsize = src_raster_ds.RasterXSize
        ysize = src_raster_ds.RasterYSize
        src_band = src_raster_ds.GetRasterBand(1)
        dtype = src_band.DataType
        src_raster_geo = src_raster_ds.GetGeoTransform()
        src_raster_prj = src_raster_ds.GetProjection()
        dst_raster_geo = list(src_raster_geo)
        dst_raster_geo[0] = point[0]
        dst_raster_geo[3] = point[1]
        drv_tif = gdal.GetDriverByName('GTiff')
        dst_ds = drv_tif.Create(dst_raster, xsize, ysize, 1, dtype)
        dst_band = dst_ds.GetRasterBand(1)
        dst_band.WriteArray(src_band.ReadAsArray())
        dst_ds.SetGeoTransform(dst_raster_geo)
        dst_ds.SetProjection(src_raster_prj)
        src_raster_ds = dst_ds = dst_band = None
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
    src_dir = r"\\192.168.0.234\nydsj\user\ZSS\1.成果栅格"
    dst_dir = r"\\192.168.0.234\nydsj\user\ZSS\2.out"
    left_point = [-38240.022, 3833587.22]
    main(src_dir, dst_dir, left_point)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
