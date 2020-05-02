#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/12/3 15:15
# @Author  : zhaoss
# @FileName: inter_bilinear.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
使用numpy的方法对影像进行双线性插值重采样

Parameters


"""

import os
import sys
import glob
import math
import copy
import time
import fnmatch
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def get_indices(source_ds, target_width, target_height):
    """
    Return x, ylists of all possible resampling offsets.
    :param source_ds: dataset to get offsets from
    :param target_width: target pixel width
    :param target_height: target pixel height (negative)
    :return: x, y lists of all possible resampling offsets
    """
    source_geotransform = source_ds.GetGeoTransform()
    source_width = source_geotransform[1]
    source_height = source_geotransform[5]
    dx = target_width / source_width
    dy = target_height / source_height
    target_x = np.arange(dx / 2, source_ds.RasterXSize, dx)
    target_y = np.arange(dy / 2, source_ds.RasterYSize, dy)

    x, y = np.meshgrid(target_x, target_y)
    x -= 0.5
    y -= 0.5
    x = np.minimum(np.maximum(x, 0), source_ds.RasterXSize - 2)
    y = np.minimum(np.maximum(y, 0), source_ds.RasterYSize - 2)
    x0 = np.floor(x).astype(int)
    x1 = x0 + 1
    y0 = np.floor(y).astype(int)
    y1 = y0 + 1
    return x, y, x0, y0, x1, y1


def main(in_fn, out_fn):
    cell_size = [0.00004, -0.00004]

    in_ds = gdal.Open(in_fn)
    bandnum = in_ds.RasterCount
    x, y, x0, y0, x1, y1 = get_indices(in_ds, *cell_size)
    rows = x.shape[0]
    cols = x.shape[1]

    driver = gdal.GetDriverByName('GTiff')
    out_ds = driver.Create(out_fn, cols, rows, bandnum, gdal.GDT_UInt16)
    out_ds.SetProjection(in_ds.GetProjection())
    gt = list(in_ds.GetGeoTransform())
    gt[1] = cell_size[0]
    gt[5] = cell_size[1]
    out_ds.SetGeoTransform(gt)
    for iband in range(bandnum):
        in_data = in_ds.GetRasterBand(iband + 1).ReadAsArray()
        out_data = in_data[y0, x0] * (y1 - y) * (x1 - x) + \
                   in_data[y0, x1] * (y1 - y) * (x - x0) + \
                   in_data[y1, x0] * (y - y0) * (x1 - x) + \
                   in_data[y1, x1] * (y - y0) * (x - x0)
        out_band = out_ds.GetRasterBand(iband + 1)
        out_band.WriteArray(out_data)
        out_band.FlushCache()
    in_ds = None
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
    in_file = r"F:\test_data\new_test\GF2_20180718_L1A0003330812_sha.tiff"
    out_file = r"F:\test_data\new_test\GF2_20180718_L1A0003330812_sha_inter_test.tiff"
    main(in_file, out_file)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
