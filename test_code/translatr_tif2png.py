#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2021/3/31 16:15
# @Author  : zhaoss
# @FileName: translatr_tif2png.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
将类似指数图结果的彩色tif影像转换为png，在转换过程中可以进行分辨率的压缩

Parameters


"""

import os
import math
import glob
import time
import fnmatch
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def tif2png(outpath, src_dst, dst_xsize, dst_ysize):
    """
    根据输入的目标影像行列数对原始影像进行缩放，缩放方法为双线性插值
    :param src_dst: 原始数据集
    :param dst_xsize: 目标影像列数
    :param dst_ysize: 目标影像行数
    :return: 返回重采样后的目标影像数据集
    """
    # 根据目标大小，在内存创建结果影像
    gdal.Translate(outpath, src_dst, resampleAlg=gdalconst.GRA_NearestNeighbour, format='PNG', width=dst_xsize,
                   height=dst_ysize, outputType=gdalconst.GDT_Byte, noData=0)
    return None


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


def corner_to_geo(sample, line, dataset):
    # 计算指定行,列号的地理坐标
    Geo_t = dataset.GetGeoTransform()
    # 计算地理坐标
    geoX = Geo_t[0] + sample * Geo_t[1]
    geoY = Geo_t[3] + line * Geo_t[5]
    return geoX, geoY


def main(src, dst):
    if os.path.isdir(src):
        files = searchfiles(src, partfileinfo='*.tif')
    else:
        files = src
    for file in files:
        basename = os.path.splitext(os.path.basename(file))[0]
        ds = gdal.Open(file)
        xsize = ds.RasterXSize
        ysize = ds.RasterYSize
        geo = ds.GetGeoTransform()
        prj = ds.GetProjection()
        oSRC = osr.SpatialReference()
        oSRC.ImportFromWkt(prj)
        if oSRC.GetAttrValue("UNIT").lower() in ["metre", "meter"]:
            new_x_size = geo[1]
            new_y_size = geo[5]
        else:
            new_x_size = geo[1] * 10 ** 5
            new_y_size = geo[5] * 10 ** 5
        # 计算输出后影像的分辨率
        res = 0.59
        fact = np.array([res / new_x_size, -res / new_y_size])
        new_xsize = math.ceil(xsize / fact[0])
        new_ysize = math.ceil(ysize / fact[1])
        dst_file = os.path.join(dst, basename) + '_color.png'
        tif2png(dst_file, ds, new_xsize, new_ysize)
        drx, dry = corner_to_geo(xsize, ysize, ds)
        corner_coor = [str(k) for k in [geo[0], geo[3], drx, dry]]
        xml_file = os.path.join(dst, basename) + '_color.png.aux.xml'
        os.remove(xml_file)
        tfw = os.path.join(dst, basename) + '_color.tfw'
        with open(tfw, 'w', newline='') as f:
            f.write(','.join(corner_coor))
        ds = None
        pass
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
    src_dir = r"F:\test\tiles\ori"
    dst_dir = r"F:\test\tiles\out"
    main(src_dir, dst_dir)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
