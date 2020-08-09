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


def add_ARVI(blue=None, green=None, red=None, red_edge1=None, red_edge2=None, red_edge3=None, inf=None):
    """
    增加VI4指数
    :param blue:
    :param green:
    :param red:
    :param red_edge1:
    :param red_edge2:
    :param red_edge3:
    :param inf:
    :return:
    """
    blue = blue.astype(np.float32) / 10000
    red = red.astype(np.float32) / 10000
    inf = inf.astype(np.float32) / 10000
    ARVI = (inf - 2 * red + blue) / (inf + 2 * red - blue + 0.000001)
    ARVI = (ARVI * 1000).astype(np.int16)
    blue = green = red = inf = None
    return ARVI


def add_VI7(blue=None, green=None, red=None, red_edge1=None, red_edge2=None, red_edge3=None, inf=None):
    """
    增加VI4指数
    :param blue:
    :param green:
    :param red:
    :param red_edge1:
    :param red_edge2:
    :param red_edge3:
    :param inf:
    :return:
    """
    blue = blue.astype(np.float32) / 10000
    green = green.astype(np.float32) / 10000
    red = red.astype(np.float32) / 10000
    inf = inf.astype(np.float32) / 10000
    VI7 = (blue + green + red) * (inf + red) / (inf - red + 0.000001)
    VI7 = (VI7 * 1000).astype(np.int16)
    blue = green = red = inf = None
    return VI7


def add_VI4(blue=None, green=None, red=None, red_edge1=None, red_edge2=None, red_edge3=None, inf=None):
    """
    增加VI4指数
    :param blue:
    :param green:
    :param red:
    :param red_edge1:
    :param red_edge2:
    :param red_edge3:
    :param inf:
    :return:
    """
    blue = blue.astype(np.int16)
    green = green.astype(np.int16)
    red = red.astype(np.int16)
    VI4 = blue + green + red
    blue = green = red = None
    return VI4


def add_msavi(blue=None, green=None, red=None, red_edge1=None, red_edge2=None, red_edge3=None, inf=None):
    """
    针对含有红边波段的哨兵数据添加msavi指数
    :param blue:
    :param green:
    :param red:
    :param red_edge1:
    :param red_edge2:
    :param red_edge3:
    :param inf:
    :return:
    """
    red = red.astype(np.float32) / 10000
    inf = inf.astype(np.float32) / 10000
    msavi = (inf + 0.5 - np.sqrt((inf + 0.5) * (inf + 0.5) - 2 * (inf - red))) * 1000
    msavi = msavi.astype(np.int16)
    red = inf = None
    return msavi


def add_mtci(blue=None, green=None, red=None, red_edge1=None, red_edge2=None, red_edge3=None, inf=None):
    """
    针对含有红边波段的哨兵数据添加mtci指数
    :param blue:
    :param green:
    :param red:
    :param red_edge1:
    :param red_edge2:
    :param red_edge3:
    :param inf:
    :return:
    """
    red_edge2 = red_edge2.astype(np.int16)
    red_edge1 = red_edge1.astype(np.int16)
    red = red.astype(np.int16)
    mtci = (((red_edge2 - red_edge1) / (red_edge1 - red + 0.000001)) * 1000).astype(np.int16)
    red_edge2 = red_edge1 = red = None
    return mtci


def add_ndvi(blue=None, green=None, red=None, red_edge1=None, red_edge2=None, red_edge3=None, inf=None):
    """
    增加归一化植被指数
    :param blue:
    :param green:
    :param red:
    :param red_edge1:
    :param red_edge2:
    :param red_edge3:
    :param inf:
    :return:
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
    index_list = [add_ndvi, add_VI4, add_VI7, add_ARVI]
    index_num = len(index_list)
    index_arr = np.zeros((index_num, ysize, xsize))
    for ifunc in range(index_num):
        func = index_list[ifunc]
        if bandnum == 4:
            index_arr[ifunc, :, :] = func(blue=oridata[0, :, :],
                                          green=oridata[1, :, :],
                                          red=oridata[2, :, :],
                                          inf=oridata[3, :, :])
        else:
            index_arr[ifunc, :, :] = func(blue=oridata[0, :, :],
                                          green=oridata[1, :, :],
                                          red=oridata[2, :, :],
                                          red_edge1=oridata[3, :, :],
                                          red_edge2=oridata[4, :, :],
                                          red_edge3=oridata[5, :, :],
                                          inf=oridata[6, :, :])
    # 写出数据
    tiff_driver = gdal.GetDriverByName('GTiff')
    all_band = bandnum + index_num
    out_ds = tiff_driver.Create(outfile, xsize, ysize, all_band, gdal.GDT_Int16)
    out_ds.SetProjection(rpj)
    out_ds.SetGeoTransform(geo)
    countband = 1
    # 写原始影像
    for iband in range(bandnum):
        out_ds.GetRasterBand(iband + 1).WriteArray(oridata[iband, :, :])
        progress(countband / all_band)
        countband += 1
    for iband in range(index_num):
        out_ds.GetRasterBand(bandnum + iband + 1).WriteArray(index_arr[iband, :, :])
        progress(countband / all_band)
        countband += 1
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
    infile = r"\\192.168.0.234\nydsj\user\ZSS\2020yancao\GF2\clip\GF2_20200707_L1A0004910794_reg_GF2_20200707_河底镇.tif"
    outfile = r"\\192.168.0.234\nydsj\user\ZSS\2020yancao\luoyang\GF2_20200707_L1A0004910794_reg_GF2_20200707_河底镇_veg.tif"
    main(infile, outfile)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
