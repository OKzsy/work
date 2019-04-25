#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/4/23 10:55
# @Author  : zhaoss
# @FileName: imgtobyte.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
    对输入的影像采用2%线性拉伸，转换为可以在线展示的影像（Data_type:Byte,
img_type:Tiff)
Parameters
    :param in_path: 待处理影像所在文件夹
    :param out_path: 输出影像所在文件夹
    :return: None
"""

import os
import glob
import time
import numpy as np
import fnmatch
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
        elif fnmatch.fnmatch(os.path.basename(mpath), partfileinfo):
            filelist.append(mpath)
        # 如果mpath为子文件夹，则进行递归调用，判断子文件夹下的文件
    return filelist


def hist(data, ratio):
    bins = np.arange(start=int(data.min()), stop=int(data.max()) + 2, step=1)
    n, xbin = np.histogram(data, bins=bins)
    nozero_index = np.where(xbin[:-1] > 0)
    zero_count = np.where(data == 0)[0].shape[0]
    n = n[nozero_index]
    xbin = xbin[nozero_index]
    # 计算累计频率
    cdf = np.cumsum(n) / (data.size - zero_count)
    # 计算对应断点
    diff = abs(cdf - ratio * 1.0 / 100)
    min_gray = xbin[np.where(diff == diff.min())]
    diff = abs(cdf - (1 - ratio * 1.0 / 100))
    max_gray = xbin[np.where(diff == diff.min())]
    return min_gray, max_gray


def Liner(ds, band_index):
    band_data = ds.GetRasterBand(band_index + 1).ReadAsArray()
    # 记录nodata位置
    zero_index = np.where(band_data == band_data[0][0])
    # 计算ratio(2%)点
    min_gray, max_gray = hist(band_data, 2)
    # 将直方图中ratio以外的值统一为min_gray和max_gray
    norm_min_data = np.where(band_data <= min_gray, min_gray, band_data)
    stretch_img = np.where(norm_min_data >= max_gray, max_gray, norm_min_data)
    # 拉伸影像
    # 确定拉伸后的范围
    low = 1
    high = 255
    stretched_img = low + (high - low) * 1.0 * (stretch_img - min_gray) / (max_gray - min_gray)
    # 反填背景值
    stretched_img[zero_index] = 0
    return stretched_img


def main(in_dir, out_dir, partfileinfo='*'):
    """

    :param in_path: 待处理影像所在文件夹
    :param out_path: 输出影像所在文件夹
    :return: None
    """
    # 搜索需要处理的影像
    Pending_images = searchfiles(in_dir, partfileinfo=partfileinfo, recursive=True)
    # 循环处理文件
    for ifile in Pending_images:
        basename = os.path.splitext(os.path.basename(ifile))[0]
        stretched_img_name = basename + '-strect.tiff'
        # 打开影像
        data_ds = gdal.Open(ifile)
        # 获取影像的基本信息
        Bandcount = data_ds.RasterCount
        xsize = data_ds.RasterXSize
        ysize = data_ds.RasterYSize
        # 控制只输出三个波段
        if Bandcount >= 3:
            Bandcount = 3
        # 创建输出影像
        stretched_img_path = os.path.join(out_dir, stretched_img_name)
        tiff_driver = gdal.GetDriverByName('GTiff')
        stretched_ds = tiff_driver.Create(stretched_img_path, xsize, ysize, Bandcount, gdal.GDT_Byte)
        stretched_ds.SetProjection(data_ds.GetProjection())
        stretched_ds.SetGeoTransform(data_ds.GetGeoTransform())
        # 循环波段拉伸处理
        for iband in range(Bandcount):
            stretched_band = Liner(data_ds, iband)
            print('Start outputting the {0} band'.format(iband + 1))
            stretched_ds.GetRasterBand(Bandcount - iband).WriteArray(stretched_band, callback=progress)
        data_ds = None
        stretched_ds = None
    return None


if __name__ == '__main__':
    # 支持中文路径
    gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "NO")
    # 注册所有gdal驱动
    gdal.AllRegister()
    start_time = time.clock()
    in_path = r"\\192.168.0.234\nydsj\user\ZSS\testaera"
    out_path = r"\\192.168.0.234\nydsj\user\ZSS\testaera"
    partfileinfo = "*L1A0002985953_sha.tif"
    main(in_path, out_path, partfileinfo=partfileinfo)
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
