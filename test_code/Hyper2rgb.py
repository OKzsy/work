#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/6/28 9:48
# @Author  : zhaoss
# @FileName: Hyper2rgb.py
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


def main(image, out):
    basename = os.path.basename(image)
    outpath = os.path.join(out, basename)
    data_ds = gdal.Open(image)
    xsize = data_ds.RasterXSize
    ysize = data_ds.RasterYSize
    bandCount = 3
    driver = gdal.GetDriverByName("GTiff")
    out_ds = driver.Create(outpath, xsize, ysize, bandCount, gdal.GDT_UInt16)
    out_ds.SetProjection(data_ds.GetProjection())
    out_ds.SetGeoTransform(data_ds.GetGeoTransform())
    for iband in range(bandCount):
        temp_arr = data_ds.GetRasterBand(iband + 1).ReadAsArray()
        out_ds.GetRasterBand(iband + 1).WriteArray(temp_arr)
    out_ds.FlushCache()
    return None


if __name__ == '__main__':
    start_time = time.clock()
    hyper = r"\\192.168.0.234\nydsj\user\LT\20190626\test\GF2_20190510_L1A0003990501_1.tif"
    out = r"\\192.168.0.234\nydsj\user\LT\20190626\test\test_out"
    main(hyper, out)
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))


