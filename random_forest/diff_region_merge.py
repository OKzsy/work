#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2026/07/05 21:22
# @Author  : zhaoss
# @FileName: diff_region_merge.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Descriptio
一个区域的完整分类识别结果，有可能需要数次，将数次的结果拼接为一个完整结果
Parameters

"""

import os
import time
import glob
import fnmatch
import shutil
import tempfile
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def searchfiles(dirpath, partfileinfo="*", recursive=False):
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


def sort_files(files_path):
    # 从输入的文件名中获取填补顺序，并对应的将其路径排序
    file_dict = {}
    for ifile in files_path:
        # 获取区域名字
        aera_name_part = os.path.basename(ifile).split("_")[2]
        aera_name_list = aera_name_part.split("-")
        if len(aera_name_list) == 1:
            file_dict[0] = ifile
        else:
            file_dict[int(aera_name_list[1])] = ifile
    # 排序
    sorted_file_path = {}
    for idx in sorted(file_dict.keys()):
        sorted_file_path[idx] = file_dict[idx]
    return sorted_file_path


def tif_merge(in_path_list, out_path, temp_dir, in_nodata, out_nodata):
    """影像镶嵌"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".vrt", delete=False, dir=temp_dir
    ) as tmp:
        vrt_file = tmp.name
    in_file_list = [str(file) for file in in_path_list]
    vrt_options = gdal.BuildVRTOptions(
        srcNodata=str(in_nodata), VRTNodata=str(out_nodata), hideNodata=True
    )
    gdal.BuildVRT(vrt_file, in_file_list, options=vrt_options)
    out_driver = gdal.GetDriverByName("GTiff")
    if os.path.exists(out_path):
        out_driver.Delete(out_path)
    vrt_ds = gdal.Open(vrt_file)
    out_ds = out_driver.CreateCopy(out_path, vrt_ds, callback=progress)
    out_ds.FlushCache()
    out_ds = vrt_ds = None
    os.remove(vrt_file)
    return None


def main(shp_folder, uncomplete_folder, out_folder):
    # 从单个shp中获取区域名称
    area_shapefile = searchfiles(shp_folder, partfileinfo="*.shp")
    # 追一镶嵌
    for iarea_file in area_shapefile:
        shp_basename = os.path.splitext(os.path.basename(iarea_file))[0]
        area_name = shp_basename.split("-")[0]
        # area_name = "bole"
        partfileinfo = f"*{area_name}*.tif"
        uncomplete_files = searchfiles(
            uncomplete_folder, recursive=False, partfileinfo=partfileinfo
        )
        # 对获取的过程结果进行排序，拼接。排序规则是，后续补充的结果压盖前面的结果
        if len(uncomplete_files) == 0:
            # 该区域第一次就处理完整了，不需要重新处理，拷贝到指定的目录
            print(f"The {area_name} has been complete!")
            shutil.copy(uncomplete_files[0], out_folder)
            continue
        # 对于查找到的所有过程分类结果进行排序，按照填补顺序排序
        sorted_uncomplete_files = sort_files(uncomplete_files)
        # 镶嵌
        merge_name = shp_basename + "_merge.tif"
        out_path = os.path.join(out_folder, merge_name)
        in_file_list = [file_path for idx, file_path in sorted_uncomplete_files.items()]
        tif_merge(in_file_list, out_path, out_folder, 0, 0)
        pass
    return None


if __name__ == "__main__":
    # 支持中文路径
    gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
    # 支持中文属性字段
    gdal.SetConfigOption("SHAPE_ENCODING", "GBK")
    # 注册所有ogr驱动
    ogr.RegisterAll()
    # 注册所有gdal驱动
    gdal.AllRegister()
    start_time = time.time()
    init_shp_folder = r"F:\cotton\finalMap\2025\north-15\bu"
    uncomplete_class_folder = r"F:\cotton\finalMap\2025\north-30\bu"
    complete_class_folder = r"F:\cotton\finalMap\2025\north-30"
    main(init_shp_folder, uncomplete_class_folder, complete_class_folder)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
