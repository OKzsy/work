#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/8/29 16:51

parameters
    in_file: input file path
    out_file: output file path
    shape_file: shapefile path

"""

import sys
import time
import os

try:
    from osgeo import gdal
except ImportError:
    import gdal

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress

def main(in_file, out_file, shapefile):

    gdal.SetConfigOption('GDALWARP_IGNORE_BAD_CUTLINE', 'YES')
    tiff_driver = gdal.GetDriverByName("GTiff")
    if os.path.exists(out_file):
        tiff_driver.Delete(out_file)

    # gdal.Warp(out_file, in_file, cutlineDSName=shapefile, cropToCutline=True,
    #           srcNodata=srcnodata, dstNodata=dstnodata, multithread=True,
    #           callback=progress, resampleAlg=gdal.GRIORA_Bilinear)
    res = os.system("/usr/local/bin/gdalwarp/gdalwarp %s %s  -srcnodata %s -dstnodata %s -cutline %s \
                    -t_srs EPSG:4326 -overwrite -wo NUM_THREADS=ALL_CPUS -wm 4096 -co TILED=YES"
                     % (in_file, out_file, srcnodata, dstnodata, shapefile))
    if res is not None and res == 0:
        print("wrap successfully.")


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
