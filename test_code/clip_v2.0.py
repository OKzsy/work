#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/9/7 19:15

Description:
    利用shapefile裁剪影像，输出背景值为0的影像

Parameters
    参数1: 输入待裁剪的影像路径
    参数2: 输入shapefile路径
    参数3: 输出裁切影像路径

"""

import os
import sys
import time
import psutil
import subprocess
import platform

try:
    from osgeo import gdal, ogr
except ImportError:
    import gdal, ogr

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def main(in_file, shapefile, out_file):
    # 单位为字节
    total_memory = psutil.virtual_memory().total
    #
    sys_str = platform.system()
    if (sys_str == 'Windows'):
        warp_path = 'gdalwarp'
    else:
        warp_path = '/usr/local/bin/gdalwarp'

    clip_cmd_str = '%s --config GDAL_FILENAME_IS_UTF8 NO --config GDALWARP_IGNORE_BAD_CUTLINE YES -srcnodata %d -dstnodata %d -crop_to_cutline' \
                   ' -cutline %s -of GTiff -r bilinear -overwrite -wm %d -wo NUM_THREADS=ALL_CPUS -co TILED=YES %s %s' \
                   % (warp_path, 0, 0, shapefile, 4096, in_file, out_file)

    print(clip_cmd_str)
    subprocess.call(clip_cmd_str, shell=True)


if __name__ == '__main__':
    start_time = time.time()

    # if len(sys.argv[1:]) < 3:
    #     sys.exit('Problem reading input')
    # main(sys.argv[1], sys.argv[2], sys.argv[3])

    # if len(sys.argv[1:]) < 2:
    #     sys.exit('Problem reading input')

    in_file = r"\\192.168.0.234\nydsj\common\2.data\2.google\zhengzhou\gongyishi\gongyishi\gongyishi.tif"
    shape_file = r"F:\temp\gongyi-201804-guge.shp"
    out_file = r"F:\temp\gongyi-201804-guge.tif"
    main(in_file, shape_file, out_file)

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))
