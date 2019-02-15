#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Author:zhaoss
Email:zhaoshaoshuai@hnnydsj.com
Create date:  
File: .py
Description:


Parameters


"""
import os
import glob
import time
import sys
import numpy as np
import math
from osgeo import gdal, ogr, gdalconst


def main(templateTifFileName, shpFileName, outputFileName):
    data = gdal.Open(templateTifFileName, gdalconst.GA_ReadOnly)
    prj = data.GetProjection()
    geo_transform = data.GetGeoTransform()
    x_min = geo_transform[0]
    y_min = geo_transform[3]
    x_res = data.RasterXSize
    y_res = data.RasterYSize
    mb_v = ogr.Open(shpFileName)
    mb_l = mb_v.GetLayer()
    ext = mb_l.GetExtent(force=True)
    print(ext)
    pixel_width = geo_transform[1]
    target_ds = gdal.GetDriverByName('GTiff').Create(outputFileName, x_res, y_res, 1, gdal.GDT_Byte)
    target_ds.SetProjection(prj)
    target_ds.SetGeoTransform((x_min, pixel_width, 0, y_min, 0, -1 * pixel_width))
    band = target_ds.GetRasterBand(1)
    NoData_value = -999
    band.SetNoDataValue(NoData_value)
    band.FlushCache()
    gdal.RasterizeLayer(target_ds, [1], mb_l)
    target_ds = None


if __name__ == '__main__':
    start_time = time.clock()
    in_file = r"F:\test_data\clipraster\SatImage.tif"
    shpfile = r"F:\test_data\clipraster\county.shp"
    outfile = r"F:\test_data\clipraster\gdal_mask2\test_country_mask.tif"

    main(in_file, shpfile, outfile)

    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
