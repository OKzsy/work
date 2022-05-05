#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2021/12/7 8:38
# @Author  : zhaoss
# @FileName: inv_ireci.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
该指数与植物冠层叶绿素含量和叶面积指数具有很好的相关关系，可定量表征植物的叶绿素含量
《Evaluating the capabilities of Sentinel-2 for quantitative estimationof biophysical variables in vegetation》
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


def main(file, dst):
    # 判断输入的是否为文件
    if os.path.isdir(file):
        rasters = searchfiles(file, partfileinfo='*.tif')
    else:
        rasters = [file]
    for src in rasters:
        # 打开原始影像
        src_ds = gdal.Open(src)
        basename = os.path.basename(src)
        src_geo = src_ds.GetGeoTransform()
        src_prj = src_ds.GetProjection()
        src_xsize = src_ds.RasterXSize
        src_ysize = src_ds.RasterYSize
        # 获取计算IRECI用的波段
        b_4_665 = src_ds.GetRasterBand(3).ReadAsArray() / 10000
        b_5_705 = src_ds.GetRasterBand(4).ReadAsArray() / 10000
        b_6_740 = src_ds.GetRasterBand(5).ReadAsArray() / 10000
        b_7_783 = src_ds.GetRasterBand(6).ReadAsArray() / 10000
        ireci = (b_7_783 - b_4_665) / ((b_5_705 / (b_6_740 + 0.00001)) + 0.00001)
        ireci = np.round(ireci, 3)
        # 创建输出文件
        drv = gdal.GetDriverByName('GTiff')
        dst_dir = os.path.join(dst, basename)
        dst_ds = drv.Create(dst_dir, src_xsize, src_ysize, 1, gdal.GDT_Float32)
        dst_ds.SetGeoTransform(src_geo)
        dst_ds.SetProjection(src_prj)
        dst_ds.GetRasterBand(1).WriteArray(ireci, callback=progress)
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
    src_file = r'\\192.168.0.234\nydsj\project\39.鹤壁高标准良田\1.data\S2\2.atm\2021年\12月'
    dst_file = r'\\192.168.0.234\nydsj\user\ZSS\qixian_yanshi\test'
    main(src_file, dst_file)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
