#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2021/4/7 15:25
# @Author  : zhaoss
# @FileName: locatDn.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
根据输入的经纬度，获取对应点的值

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
        elif fnmatch.fnmatch(mpath, partfileinfo):
            filelist.append(mpath)
        # 如果mpath为子文件夹，则进行递归调用，判断子文件夹下的文件

    return filelist


def geo_to_corner(point_coor, raster_geo):
    # 计算逆放射变换系数
    raster_inv_geo = gdal.InvGeoTransform(raster_geo)
    off_ulx, off_uly = map(round, gdal.ApplyGeoTransform(raster_inv_geo, point_coor[1], point_coor[0]))
    return off_ulx, off_uly


# 窗口索引
def win_index(anchor_x, anchor_y, cols, rows, radius):
    """

    :param anchor_x: 锚点位置（列）
    :param anchor_y: 锚点位置（行）
    :param cols: 原始影像列宽
    :param rows: 原始影像行宽
    :param radius: 窗口半径
    :return: 窗口在原始影像中的位置索引
    """
    star_x = -radius if (anchor_x - radius) > 0 else -anchor_x
    star_y = -radius if (anchor_y - radius) > 0 else -anchor_y
    end_x = radius if (cols - anchor_x - radius) > 1 else (cols - anchor_x - 1)
    end_y = radius if (rows - anchor_y - radius) > 1 else (rows - anchor_y - 1)
    # 生成所在区域窗口位置索引
    x = list(range(star_x + anchor_x, end_x + 1 + anchor_x))
    y = list(range(star_y + anchor_y, end_y + 1 + anchor_y))
    index = np.meshgrid(x, y)
    return index


def main(txt, src):
    src_ds = gdal.Open(src)
    xsize = src_ds.RasterXSize
    ysize = src_ds.RasterYSize
    src_arr = src_ds.ReadAsArray()
    geo = src_ds.GetGeoTransform()
    # 获取经纬度
    with open(txt, 'r') as f:
        lines = f.readlines()
    fj = open(txt, 'w', newline='')
    for line in lines:
        line = line.rstrip().split(',')
        coor = [float(k) for k in line[:2]]
        sample, row = geo_to_corner(coor, geo)
        # 按照窗口取平均值
        # 按照0.5m
        win_size = 3
        index = win_index(sample, row, xsize, ysize, int((win_size - 1) / 2))
        win_value = src_arr[index[1], index[0]]
        value = np.mean(win_value)
        line.append(str(value))
        line = ','.join(line)
        fj.write(line)
        fj.write('\n')
    fj.close()
    src_ds = None
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
    txtfile = r"F:\test\idw\locate0.125.txt"
    var = [-1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    # src_file = r"F:\test\idw\idw_color_3_9.tif"
    for k in var:
        src_file = r"F:\test\idw\idw_color_0.125_{}.tif".format(k)
        print(src_file)
        main(txtfile, src_file)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
