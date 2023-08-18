#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2023/07/17 14:54
# @Author  : zhaoss
# @FileName: imgInfoExtra.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
通过数据的shp文件(包含点和面), 从影像上提取对应位置或者区域信息
Parameters

"""
import os
import time
import glob
import fnmatch
import numpy as np
from datetime import datetime
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress

def searchfiles(dirpath, partfileinfo='*', recursive=False):
    """列出符合条件的文件(包含路径), 默认不进行递归查询,当recursive为True时同时查询子文件夹"""
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


def main(yieldMeasure, src, yield2img):
    # 查询所有数据
    # 判断输入的是否为文件
    if os.path.isdir(src):
        rasters = searchfiles(src, partfileinfo='*.tif')
    else:
        rasters = [src]
    # 获取测产基本数据
    # 获取原始信息
    fj = open(yieldMeasure, 'r', encoding='utf-8')
    lines = fj.read().splitlines()
    # 输出文件
    ofj = open(yield2img, 'w', encoding='utf-8')
    ofj.write(','.join(['datetime', 'diffDays', 'yield', 'viValue']))
    ofj.write('\n')
    # 逐影像进行处理
    # 窗口半径大小
    radius = int(3 / 2)
    # 播种日期
    startdt = datetime.strptime('20211001',"%Y%m%d")
    for raster in rasters:
        # 获取影像时间
        basename = os.path.splitext(os.path.basename(raster))[0]
        longtime = basename.split('_')[3]
        shorttime = longtime.split('T')[0]
        localdt = datetime.strptime(shorttime,"%Y%m%d")
        diffDay = (localdt - startdt).days
        # 获取影像数据
        ds = gdal.Open(raster)
        # 获取栅格的放射变换参数
        raster_geo = ds.GetGeoTransform()
        # 计算逆放射变换系数
        raster_inv_geo = gdal.InvGeoTransform(raster_geo)
        viValue = ds.ReadAsArray()
        rows = viValue.shape[0]
        cols = viValue.shape[1]
        for line in lines:
            data = line.split()
            lon = float(data[0])
            lat = float(data[1])
            yieldValue = data[2]
            # 根据点位获取影像具体位置窗口内的平均值
            anchor_x, anchor_y = map(round, gdal.ApplyGeoTransform(raster_inv_geo, lon, lat))
            star_x = -radius if (anchor_x - radius) >= 0 else -anchor_x
            star_y = -radius if (anchor_y - radius) >= 0 else -anchor_y
            end_x = radius if (cols - anchor_x - radius) >= 1 else (cols - anchor_x - 1)
            end_y = radius if (rows - anchor_y - radius) >= 1 else (rows - anchor_y - 1)
             # 获取窗口数据
            xx = list(range(star_x + anchor_x, end_x + anchor_x + 1))
            yy = list(range(star_y + anchor_y, end_y + anchor_y + 1))
            grad_index = np.meshgrid(yy, xx)
            vimatrix = viValue[grad_index[0], grad_index[1]]
            # 计算窗口内大于0的平均值
            viGtZero = np.extract(vimatrix>0, vimatrix)
            vimean = np.mean(viGtZero).round(3)
            # 写出数据
            ofj.write(','.join([shorttime, str(diffDay), yieldValue, str(vimean)]))
            ofj.write('\n')
            grad_index = None
        ds = None
    fj.close()
    ofj.close()
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
    inTxt = r"F:\test\chanliang\2022年淇县测产.txt"
    srcPath = r"F:\test\chanliang\clip\msavi"
    outTxt = r"F:\test\chanliang\extra\msavi.txt"
    main(inTxt, srcPath, outTxt)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))