#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/7/3 17:08
# @Author  : zhaoss
# @FileName: shpToRaster.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import glob
import time
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def shp2raster(shp_layer, res):
    # 获取栅格数据的基本信息
    shp_prj = shp_layer.GetSpatialRef()
    if shp_prj.GetAttrValue("UNIT") == "metre":
        res = res
    else:
        res = res / 10 ** 5
    # 获取矢量的边界
    boundary = shp_layer.GetExtent()
    # 根据边界范围进行矢量栅格化
    x_size = round((boundary[1] - boundary[0]) / res)
    y_size = round((boundary[3] - boundary[2]) / res)
    # 创建mask
    # out = r"F:\test_data\mask.tif"
    # mask_ds = gdal.GetDriverByName('GTiff').Create(out, int(x_size), int(y_size), 1, gdal.GDT_Byte)
    mask_ds = gdal.GetDriverByName('MEM').Create('', int(x_size), int(y_size), 1, gdal.GDT_UInt16)
    prj = shp_prj.ExportToWkt()
    mask_ds.SetProjection(prj)
    mask_geo = [boundary[0], res, 0, boundary[3], 0, -res]
    mask_ds.SetGeoTransform(mask_geo)
    # 矢量栅格化
    print('Begin shape to mask')
    gdal.RasterizeLayer(mask_ds, [1], shp_layer, burn_values=[1], callback=progress)
    return mask_ds


def main(shp, raster, resolution):
    # 打开矢量数据
    shp_ds = ogr.Open(shp)
    lyr = shp_ds.GetLayer(0)
    # 矢量栅格化
    mem_ds = shp2raster(lyr, resolution)
    driver = gdal.GetDriverByName("GTiff")
    result = driver.CreateCopy(raster, mem_ds, strict=1, callback=progress)
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
    start_time = time.clock()
    in_shp = r"C:\Users\01\Desktop\back(3)\back\back\class0629.shp"
    out_raster = r"C:\Users\01\Desktop\back(3)\back\back\class0629.tiff"
    resolution = 0.5
    main(in_shp, out_raster, resolution)
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
