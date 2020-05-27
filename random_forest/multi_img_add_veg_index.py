#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2020/5/26 15:32
# @Author  : zhaoss
# @FileName: multi_img_add_veg_index.py
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


def main(indir, outdir):
    infiles = searchfiles(indir, partfileinfo='*.tif')
    for infile in infiles:
        basename = os.path.basename(infile)
        print(basename)
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
        ndvi = add_ndvi(red=oridata[2, :, :], inf=oridata[3, :, :])
        new_band += 1
        # 合并所有增加的指数
        index_arr = np.zeros((new_band, ysize, xsize))
        index_arr[0, :, :] = ndvi
        ndvi = None
        # 写出数据
        outfile = os.path.join(outdir, basename)
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
    indir = r"\\192.168.0.234\nydsj\user\ZSS\20200526"
    outdir = r"\\192.168.0.234\nydsj\user\ZSS\20200526"
    main(indir, outdir)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
