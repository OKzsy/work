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
import time
import fnmatch
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def get_indices(source_ds, target_res=None, target_pixels=None):
    """
    Return x, ylists of all possible resampling offsets.
    :param source_ds: dataset to get offsets from
    :param target_width: target pixel width
    :param target_height: target pixel height (negative)
    :return: x, ylists of all possible resampling offsets
    """
    source_geotransform = source_ds.GetGeoTransform()
    source_xsize = source_ds.RasterXSize
    source_ysize = source_ds.RasterYSize
    if target_pixels == None:
        target_width = target_res[0]
        target_height = target_res[1]
        source_width = source_geotransform[1]
        source_height = source_geotransform[5]
        dx = target_width / source_width
        dy = target_height / source_height
        rows = math.ceil(source_ysize / dy)
        cols = math.ceil(source_xsize / dx)
        resolution = target_res
    else:
        rows = target_height = target_pixels[0]
        cols = target_width = target_pixels[1]
        source_height = source_ysize
        source_width = source_xsize
        dx = source_width / target_width
        dy = source_height / target_height
        resolution = [source_geotransform[1] * dx, source_geotransform[5] * dy]
    target_x = np.arange(cols)
    target_y = np.arange(rows)
    src_x = (target_x + 0.5) * dx - 0.5
    src_y = (target_y + 0.5) * dy - 0.5
    src_x = np.minimum(np.maximum(src_x, 0), source_xsize - 2)
    src_y = np.minimum(np.maximum(src_y, 0), source_ysize - 2)
    src_index = np.meshgrid(src_x, src_y)
    return src_index[0], src_index[1], resolution


def bilinear(in_data, x, y):
    """
    Performs bilinear interpolation.
    :param in_data: the input dataset to be resampled
    :param x: an array of x coordinates for output pixel centers
    :param y: an array of y coordinates for output pixel centers
    :return: the interpolated data
    """
    x0 = np.floor(x).astype(int)
    x1 = x0 + 1
    y0 = np.floor(y).astype(int)
    y1 = y0 + 1

    ul = in_data[y0, x0] * (y1 - y) * (x1 - x)
    ur = in_data[y0, x1] * (y1 - y) * (x - x0)
    ll = in_data[y1, x0] * (y - y0) * (x1 - x)
    lr = in_data[y1, x1] * (y - y0) * (x - x0)

    return ul + ur + ll + lr


def main(in_fn, out_fn):
    # cell_size = [0.00004, -0.00004]
    # 行，列
    cell_number = [1210, 1240]

    in_ds = gdal.Open(in_fn)
    bandnum = in_ds.RasterCount
    # x, y, cell_res = get_indices(in_ds, target_pixels=None, target_res=cell_size)
    x, y, cell_res = get_indices(in_ds, target_pixels=cell_number, target_res=None)
    rows = x.shape[0]
    cols = x.shape[1]

    driver = gdal.GetDriverByName('GTiff')
    out_ds = driver.Create(out_fn, cols, rows, bandnum, gdal.GDT_Float32)
    out_ds.SetProjection(in_ds.GetProjection())
    gt = list(in_ds.GetGeoTransform())
    gt[1] = cell_res[0]
    gt[5] = cell_res[1]
    out_ds.SetGeoTransform(gt)
    for iband in range(bandnum):
        in_data = in_ds.GetRasterBand(iband + 1).ReadAsArray()
        out_data = bilinear(in_data, x, y)
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
    in_file = r"F:\SIFT\left_one_band.PNG"
    out_file = r"F:\SIFT\left_one_band_py.tif"
    main(in_file, out_file)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
