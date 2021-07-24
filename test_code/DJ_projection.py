#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2021/1/21 15:50
# @Author  : zhaoss
# @FileName: test_gdal.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""
import os
import time
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def def_prj(tfw, src):
    # 获取tfw信息
    fn = open(tfw, newline='')
    tfw_str = fn.readlines()
    tfw_value = [float(value) for value in tfw_str]
    fn.close
    src_ds = gdal.Open(src, 1)
    # 定义目标投影
    oSRS = osr.SpatialReference()
    oSRS.SetWellKnownGeogCS("WGS84")
    geo = [tfw_value[4], tfw_value[0], tfw_value[1], tfw_value[5], tfw_value[2], tfw_value[3]]
    src_ds.SetProjection(oSRS.ExportToWkt())
    src_ds.SetGeoTransform(geo)
    src_ds.FlushCache()
    src_ds = None
    return None


def main(root_dir):
    # 获取根目录下所有子目录
    children_dir = os.listdir(root_dir)
    for child_dir in children_dir:
        index_map_dir = os.path.join(root_dir, child_dir, 'map', 'index_map')
        index_map_color_dir = os.path.join(root_dir, child_dir, 'map', 'index_map_color')
        # 获取待处理影像
        src_files = [file for file in os.listdir(index_map_color_dir) if file.endswith('.tif')]
        for ifile in src_files:
            src_file = os.path.join(index_map_color_dir, ifile)
            src_basename = os.path.splitext(os.path.basename(src_file))[0]
            src_tfw = os.path.join(index_map_dir, src_basename) + '.tfw'
            def_prj(src_tfw, src_file)
            pass
        pass
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
    root_dir = r"\\192.168.0.234\nydsj\user\ZSS\DJI-test"
    main(root_dir)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
