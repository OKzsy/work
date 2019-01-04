#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2017.6.29
update: 2018.6.29

parameters
    in_file: input file path
    out_file: output file path
    shape_file: shapefile path

"""

import sys
import time
import os
import psutil

try:
    from osgeo import gdal
except ImportError:
    import gdal


__author__ = 'tianjg'

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress

def main(in_file, out_file, shapefile):
    # 单位为字节
    total_memory = psutil.virtual_memory().total

    gdal.SetConfigOption('GDALWARP_IGNORE_BAD_CUTLINE', 'YES')
    gdal.SetCacheMax(int(total_memory))
    tiff_driver = gdal.GetDriverByName("GTiff")
    if os.path.exists(out_file):
        tiff_driver.Delete(out_file)

    # gdal.Warp(out_file, in_file, cutlineDSName = shapefile, cropToCutline = True,
    #           srcNodata = srcnodata, dstNodata = dstnodata, multithread = True,
    #           warpMemoryLimit = int(total_memory / 4 * 3),
    #           callback = progress, resampleAlg = gdal.GRIORA_Bilinear)

    gdal.Warp(out_file, in_file, cutlineDSName=shapefile, cropToCutline=True,
              srcNodata=srcnodata, dstNodata=dstnodata, multithread=True,
              callback=progress, resampleAlg=gdal.GRIORA_Bilinear)

if __name__ == "__main__":

    start_time = time.time()


    if len(sys.argv[1:]) == 4:
        srcnodata = float(sys.argv[4])
    if len(sys.argv[1:]) == 5:
        srcnodata = float(sys.argv[4])
        dstnodata = float(sys.argv[5])
    if len(sys.argv[1:]) == 3:
        srcnodata = 0
        dstnodata = 0
    if len(sys.argv[1:]) < 3:
        sys.exit('Problem reading input')
    main(sys.argv[1], sys.argv[2], sys.argv[3])


    end_time = time.time()
    print( "time: %.2f min." % ((end_time - start_time) / 60))



