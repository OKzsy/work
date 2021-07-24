#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2021/1/21 10:49
# @Author  : zhaoss
# @FileName: images_merge.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
利用vrt文件特性对输入的多个影像进行镶嵌（后续可以增加直方图匹配或者直方图均衡）

Parameters


"""

import os
import sys
import glob
import time
import tempfile
import fnmatch
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def main(src, dst, src_nodata, dst_nodata):
    vrt_file = tempfile.mktemp(dir=os.path.dirname(dst), prefix='VRT_', suffix='.vrt')
    src_files_list = [str(file) for file in src]
    vrt_options = gdal.BuildVRTOptions(srcNodata=str(src_nodata),
                                       VRTNodata=str(dst_nodata),
                                       hideNodata=True)
    gdal.BuildVRT(vrt_file, src_files_list, options=vrt_options)
    dst_driver = gdal.GetDriverByName('GTiff')
    if os.path.exists(dst):
        dst_driver.Delete(dst)
    vrt_ds = gdal.Open(vrt_file)
    dst_ds = dst_driver.CreateCopy(dst, vrt_ds, callback=progress)
    dst_ds.FlushCache()
    dst_ds = vrt_ds = None
    os.remove(vrt_file)
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
    src_files = r"\\192.168.0.234\nydsj\user\ZSS\洛宁苹果\clip\L2A_T49SET_A017304_20200629T031704_ref_10m.tif", \
                r"\\192.168.0.234\nydsj\user\ZSS\洛宁苹果\clip\L2A_T49SEU_A026141_20200624T032157_ref_10m.tif"
    dst_file = r'\\192.168.0.234\nydsj\user\ZSS\洛宁苹果\merge\merge.tif'
    src_nodata = 0
    dst_nodata = 0
    main(src_files, dst_file, src_nodata, dst_nodata)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
