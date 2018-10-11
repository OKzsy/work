#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/3/29 9:30

Description:
    

Parameters
    

"""

import os
import sys
import time
try:
    from osgeo import gdal, gdalconst, osr
except ImportError:
    import gdal, gdalconst, osr
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

    # output envi file
    out_driver = gdal.GetDriverByName('ENVI')
    if os.path.exists(out_file):
        out_driver.Delete(out_file)

    gdal.Warp(out_file, in_file, format='ENVI',
              srcSRS=in_proj, dstSRS=match_proj,
              srcNodata=0, dstNodata=0, multithread=True,
              warpMemoryLimit=2048,
              width = match_xsize, height = match_ysize, callback=progress)


if __name__ == '__main__':

    print('program running')

    start_time = time.time()
#
#    if len(sys.argv[1:]) < 3:
#        sys.exit('Problem reading input')
#    if len(sys.argv[1:]) == 4:
#        input_proj = sys.argv[4]
#    if len(sys.argv[1:]) == 3:
#        input_proj = None
#
#    main(sys.argv[1], sys.argv[2], sys.argv[3])

    in_file=r"D:\work\project\image_fusion\image\test2\2.tif"
    match_file=r"D:\work\project\image_fusion\image\test2\1.tif"
    out_file=r"D:\work\project\image_fusion\image\test2\2_up.dat"
    main(in_file,match_file,out_file)


    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))