#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2020/7/22 15:00
# @Author  : zhaoss
# @FileName: orthorectification.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import sys
import glob
import time
import fnmatch
import shutil
import psutil
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def searchfiles(dirpath, partfileinfo='*', recursive=False):
    """列出符合条件的文件（包含路径），默认不进行递归查询，当recursive为True时同时查询子文件夹"""
    # 定义结果输出列表
    filelist = []
    # 列出根目录下包含文件夹在内的所有文件目录
    pathlist = glob.glob(os.path.join(os.path.sep, dirpath, "*"))
    # 逐文件进行判断
    for mpath in pathlist:
        if os.path.isdir(mpath):
            # 默认不判断子文件夹
            if recursive:
                filelist += searchfiles(mpath, partfileinfo, recursive)
        elif fnmatch.fnmatch(mpath, partfileinfo):
            filelist.append(mpath)
        # 如果mpath为子文件夹，则进行递归调用，判断子文件夹下的文件
    return filelist


def rpc_process(in_file, out_file, dem_file):
    # 单位为字节
    total_memory = psutil.virtual_memory().total

    gdal.SetCacheMax(int(total_memory / 1 * 2))
    tif_driver = gdal.GetDriverByName("GTiff")

    if os.path.exists(out_file):
        tif_driver.Delete(out_file)
    in_xml_file = os.path.splitext(in_file)[0] + '.xml'

    if os.path.exists(in_xml_file):
        gdal.Warp(out_file, in_file, rpc=True, multithread=True, errorThreshold=0.0,
                  resampleAlg=gdal.GRIORA_Bilinear, callback=progress,
                  transformerOptions=['RPC_DEM=%s' % dem_file])

        out_xml_file = os.path.join(os.path.dirname(out_file),
                                    '%s.xml' % os.path.splitext(os.path.basename(out_file))[0])
        shutil.copy(in_xml_file, out_xml_file)

    json_file = searchfiles(os.path.dirname(in_file), '*.json')

    if json_file != []:
        if searchfiles(os.path.dirname(in_file), '*.txt') == []:

            gdal.Warp(out_file, in_file, multithread=True, errorThreshold=0.0,
                      resampleAlg=gdal.GRIORA_Bilinear, callback=progress,
                      transformerOptions=['RPC_DEM=%s' % dem_file])
        else:
            gdal.Warp(out_file, in_file, rpc=True, multithread=True, errorThreshold=0.0,
                      resampleAlg=gdal.GRIORA_Bilinear, callback=progress,
                      transformerOptions=['RPC_DEM=%s' % dem_file])
        out_json_file = os.path.join(os.path.dirname(out_file),
                                     '%s.json' % os.path.splitext(os.path.basename(out_file))[0])
        shutil.copy(json_file[0], out_json_file)
    return None


def main(src_dir, dst_dir, dem_file):
    # 判断src_dir是否为目录
    if os.path.isdir(src_dir):
        src_files = searchfiles(src_dir, partfileinfo='*.tiff')
    else:
        src_files = [src_dir]
    for src_file in src_files:
        basename = os.path.basename(src_file)
        basename = basename.replace('.tiff', '-rpc.tif')
        dst_file = os.path.join(dst_dir, basename)
        rpc_process(src_file, dst_file, dem_file)
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
    src_dir = r'\\192.168.0.234\nydsj\user\ZSS\2020yancao\洛阳20200707烟草\GF2_PMS2_E111.8_N34.5_20200707_L1A0004910794.tar\GF2_PMS2_E111.8_N34.5_20200707_L1A0004910794'
    dst_dir = r'\\192.168.0.234\nydsj\user\ZSS\2020yancao\GF2\rpc'
    dem_file = r'\\192.168.0.234\nydsj\project\2.zhiyan\3.2020\2.data\3.DEM\洛阳\2景GF.tif'
    main(src_dir, dst_dir, dem_file)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
