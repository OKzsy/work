#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/2/18 9:55
# @Author  : zhaoss
# @FileName: Distinguish_species.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import glob
import fnmatch
import time
import numpy as np
from osgeo import ogr, gdal, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def searchfiles(dirpath, partfileinfo='*', recursive=False, Directory=False):
    """列出符合条件的文件（包含路径），默认不进行递归查询，当recursive为True时同时查询子文件夹"""
    # 定义结果输出列表
    filelist = []
    # 列出根目录下包含文件夹在内的所有路径
    pathlist = glob.glob(os.path.join(os.path.sep, dirpath, "*"))
    # 逐路径进行判断
    for mpath in pathlist:
        if Directory:
            # 返回的为目录，默认不进行递归判断
            if os.path.isdir(mpath):
                if fnmatch.fnmatch(mpath, partfileinfo):
                    filelist.append(mpath)
                    filelist += searchfiles(mpath, partfileinfo, recursive, Directory)
                elif recursive:
                    filelist += searchfiles(mpath, partfileinfo, recursive, Directory)
            else:
                continue
        elif os.path.isdir(mpath):
            # 返回的为文件，默认不进行递归判断
            if recursive:
                # 如果mpath为子文件夹，则进行递归调用，判断子文件夹下的文件
                filelist += searchfiles(mpath, partfileinfo, recursive, Directory)
        elif fnmatch.fnmatch(mpath, partfileinfo):
            filelist.append(mpath)
    return filelist


def cal_NDVI(in_file):
    """计算输入影像的NDVI"""
    # 打开影像
    in_ds = gdal.Open(in_file)
    # 读取数据
    red = in_ds.GetRasterBand(3).ReadAsArray()
    nir = in_ds.GetRasterBand(4).ReadAsArray()
    # 选取非0像元
    nozero_index = np.where(red > 0)
    # 计算NDVI
    ndvi = (nir[nozero_index] - red[nozero_index]) / (nir[nozero_index] + red[nozero_index])
    # 按照20%去除异常点
    perindex = np.percentile(ndvi, q=[20, 80])
    ndvi = ndvi[np.where((ndvi >= perindex[0]) & (ndvi <= perindex[1]))]
    if len(ndvi) == 0:
        return -1
    ndvi_mean = np.mean(ndvi)
    in_ds = None
    return ndvi_mean


def main(inpath, txt):
    # 列出待处理影像文件夹
    # path_lists = searchfiles(inpath, Directory=True)
    path_lists = [os.path.join(inpath, 'changlvkuoyelin'),
                  os.path.join(inpath, 'luoyekuoyelin'),
                  os.path.join(inpath, 'zhenkuohunjiaolin'),
                  os.path.join(inpath, 'zhenyelin')]
    # 逐文件夹进行计算
    all_mean_list = []
    for path in path_lists:
        file_lists = searchfiles(path, '*.tiff')
        mean_list = []
        for file in file_lists:
            mean = cal_NDVI(file)
            if mean == -1:
                continue
            mean_list.append(mean)
        # 计算总体平均值
        all_mean = round(np.mean(np.array(mean_list)), 4)
        all_mean_list.append(all_mean)
        all_mean_str = list(map(str, all_mean_list))
    # 输出结果到txt
    with open(txt, mode='a') as fb:
        fb.write(','.join(all_mean_str))
        fb.write('\n')
    return None


if __name__ == '__main__':
    # 注册gdal驱动
    gdal.AllRegister()

    start_time = time.clock()
    in_file_path = r"F:\ChangeMonitoring\sample\2017\12"
    out_txt = r"F:\ChangeMonitoring\sample\2017\result.txt"
    main(in_file_path, out_txt)
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
