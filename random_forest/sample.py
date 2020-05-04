#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2020/4/30 15:58
# @Author  : zhaoss
# @FileName: sample.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import sys
import glob
import time
import fnmatch
import tempfile
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def searchfiles(dirpath, partfileinfo='*', recursive=False):
    """列出符合条件的文件（包含路径），默认不进行递归查询，当recursive为True时同时查询子文件夹
        并返回品类列表
    """
    # 定义结果输出列表
    filelist = []
    catelist = []
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
            basename = os.path.splitext(os.path.basename(mpath))[0]
            cate = basename.split('-')[-1]
            if cate not in catelist:
                catelist.append(cate)

    return filelist, catelist


def img2csv(sample, tmp_csv_path, flag):
    """
    将影像中符合要求的像元转换成符合要求的格式进行训练
    :param sample: 样本影像路径
    :param flag: 样本标签
    :return:
    """
    basename = os.path.splitext(os.path.basename(sample))[0]
    iflag_name = basename.split('-')[-1]
    iflag = flag[iflag_name]

    return None


def main(flag_file, sample_file, out_csv):
    # 获取标签
    flag = np.genfromtxt(flag_file, delimiter=',', dtype=None, encoding='utf8')
    flag_dict = dict(flag)
    # 处理每一个样本
    sample_list, category = searchfiles(sample_file, partfileinfo='*.tif')
    tmp_csv_path = tempfile.mkdtemp(dir=os.path.dirname(out_csv))
    for isample in sample_list:
        img2csv(isample, tmp_csv_path, flag_dict)
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
    flag_file = r"F:\test_data\dengfeng\flag.csv"
    sample_file = r"F:\test_data\dengfeng\out"
    out_csv = r"F:\test_data\dengfeng\sample.csv"
    main(flag_file, sample_file, out_csv)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
