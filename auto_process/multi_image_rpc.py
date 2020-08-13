#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/7/1 14:58
# @Author  : zhaoss
# @FileName: multi_image_rpc.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import glob
import sys
import time
import fnmatch
import shutil
import psutil
from osgeo import gdal, ogr, osr, gdalconst

try:
    from osgeo import gdal
except ImportError:
    import gdal, gdalconst
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
        elif fnmatch.fnmatch(os.path.basename(mpath), partfileinfo):
            filelist.append(mpath)
        # 如果mpath为子文件夹，则进行递归调用，判断子文件夹下的文件

    return filelist


def search_file(folder_path, file_extension):
    search_files = []
    for dir_path, dir_names, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(file_extension):
                search_files.append(os.path.normpath(os.path.join(dir_path, file)))
    return search_files


def rpc(in_file, out_file, dem_file):
    # 单位为字节
    total_memory = psutil.virtual_memory().total

    gdal.SetCacheMax(int(total_memory / 1 * 2))
    #
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

    json_file = search_file(os.path.dirname(in_file), '.json')

    if json_file != []:
        if search_file(os.path.dirname(in_file), '.txt') == []:

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


def main(in_dir, out_dir, dem_file):
    # 搜索待处理影像
    files = searchfiles(in_dir, partfileinfo="*.tiff")
    for file in files:
        basename = os.path.splitext(os.path.basename(file))[0]
        outpath = os.path.join(out_dir, basename) + "-rpc.tiff"
        rpc(file, outpath, dem_file)
    return None


if __name__ == "__main__":
    gdal.AllRegister()
    gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
    start_time = time.time()
    in_file = r"\\192.168.0.234\nydsj\project\13.重庆江津区花椒\2.data\4.GF2_2018\1.source"
    out_file = r"\\192.168.0.234\nydsj\user\ZSS\chonqinghuajiao\GF2"
    dem_file = r"\\192.168.0.234\nydsj\project\13.重庆江津区花椒\2.data\1.google\1.DEM\GF2范围\GF2范围.tif"
    main(in_file, out_file, dem_file)

    # if len(sys.argv[1:]) < 3:
    #     sys.exit('Problem reading input')
    # main(sys.argv[1], sys.argv[2], sys.argv[3])

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))
