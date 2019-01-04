#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/6/6 9:19

Description:
    

Parameters
    

"""

import os
import sys
import time
import psutil


try:
    from osgeo import gdal
except ImportError:
    import gdal

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def main(in_file, match_file, out_file):

    source_dataset = gdal.Open(in_file)
    if source_dataset is None:
        sys.exit('Problem opening file %s !' % in_file)

    # 获取数据基本信息
    xsize = source_dataset.RasterXSize
    ysize = source_dataset.RasterYSize
    num_band = source_dataset.RasterCount
    data_type = source_dataset.GetRasterBand(1).DataType

    in_geo = source_dataset.GetGeoTransform()
    in_proj = source_dataset.GetProjectionRef()

    # 获取数据基本信息
    match_dataset = gdal.Open(match_file)
    if match_dataset is None:
        sys.exit('Problem opening file %s !' % match_file)
    match_xsize = match_dataset.RasterXSize
    match_ysize = match_dataset.RasterYSize

    match_geo = match_dataset.GetGeoTransform()
    match_proj = match_dataset.GetProjectionRef()

    # output geotiff file
    out_driver = gdal.GetDriverByName('GTiff')
    if os.path.exists(out_file):
        out_driver.Delete(out_file)

    # 单位为字节
    total_memory = psutil.virtual_memory().total

    gdal.Warp(out_file, in_file, format='GTiff',
              srcSRS=in_proj, dstSRS=match_proj,
              srcNodata=0, dstNodata=0, multithread=True,
              warpMemoryLimit= int(total_memory / 3), resampleAlg = gdal.GRIORA_Bilinear,
              width = match_xsize, height = match_ysize, callback=progress)


if __name__ == '__main__':

    start_time = time.time()

    if len(sys.argv[1:]) < 3:
        sys.exit('Problem reading input')

    main(sys.argv[1], sys.argv[2], sys.argv[3])

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))