#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import glob
import time
from osgeo import gdal
from osgeo.gdalconst import *

if __name__ == '__main__':
    start_time = time.clock()
    gdal.AllRegister()
    # 使用只读方式打开图像
    imgpath = r"F:\GDAL\GDAL书籍数据\10-Data\pct.tif"
    ds = gdal.Open(imgpath, GA_ReadOnly)

    # 输出图像的格式信息
    short_img_format = ds.GetDriver().ShortName
    long_img_format = ds.GetDriver().LongName

    # 输出图像的大小和波段个数
    xsize = ds.RasterXSize
    ysize = ds.RasterYSize
    bandcount = ds.RasterCount

    # 输出图像的投影信息
    img_pro = ds.GetProjectionRef()

    # 输出图像的坐标和分辨率信息
    img_geo = ds.GetGeoTransform()

    # 获取影像的第一个波段
    band1 = ds.GetRasterBand(1)

    # 读取图像的第一行数据
    data = band1.ReadRaster(0, 0, xsize, 1, xsize, 1, band1.DataType)
    print(type(data))

    print(img_geo)

    print(img_pro)
    print(xsize, ysize, bandcount)
    print(short_img_format)
    print(long_img_format)

    ds.FlushCache()

    ds = None

    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
