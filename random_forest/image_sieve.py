#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2020/5/29 16:41
# @Author  : zhaoss
# @FileName: image_sieve.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import sys
import glob
import time
import fnmatch
import multiprocessing.dummy as mp
import numpy as np
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


def Extend(xs, ys, matrix, default_value):
    """
    根据滤波模板的大小，对原始影像矩阵进行外扩。
    :param xs: 滤波模板的xsize，要求为奇数
    :param ys: 滤波模板的ysize，要求为奇数
    :param matrix: 原始影像矩阵
    :return: 依据模板大小扩展后的矩阵
    """
    xs_fill = int((xs - 1) / 2)
    ys_fill = int((ys - 1) / 2)
    # 使用镜像填充
    extended_val = np.pad(matrix, ((ys_fill, ys_fill), (xs_fill, xs_fill)), 'constant', constant_values=default_value)
    matrix = None
    return extended_val


def gray_filtering(xs, ys, ori_xsize, ori_ysize, kernel, ext_img):
    """

    :param xs: 卷积核大小：列
    :param ys: 卷积核大小：行
    :param kernel: 卷积核
    :param ext_img: 经扩展后的影像
    :return: 滤波后的影像
    """
    # 使用切片后影像的波段书
    # 创建切片后存储矩阵
    index = np.where(kernel == 1)
    channel = kernel.size
    filtered_img = np.zeros((channel, ori_ysize, ori_xsize), dtype=np.uint8)
    ichannel = 0
    for irow in range(ys):
        for icol in range(xs):
            filtered_img[ichannel, :, :] = ext_img[irow: irow + ori_ysize, icol: icol + ori_xsize]
            ichannel += 1
    return filtered_img[index[0], :, :]


def gray_erode(win_size, kernel, src_data):
    ysize, xsize = src_data.shape
    extend_src_data = Extend(win_size, win_size, src_data, default_value=255)
    filter_img = gray_filtering(int(win_size), int(win_size), xsize, ysize, kernel, extend_src_data)
    dst_img = np.min(filter_img, axis=0)
    filter_img = None
    return dst_img


def gray_dilate(win_size, kernel, src_data):
    ysize, xsize = src_data.shape
    extend_src_data = Extend(win_size, win_size, src_data, default_value=0)
    filter_img = gray_filtering(int(win_size), int(win_size), xsize, ysize, kernel, extend_src_data)
    dst_img = np.max(filter_img, axis=0)
    filter_img = None
    return dst_img


def opening(win_size, kernel, thr, src_data):
    """
    先腐蚀后膨胀，光滑目标轮廓，消除小目标（如去掉毛刺和孤立点），在纤细出分离物体，常用于去除小颗粒噪声以及断开目标之间的粘连
    :param win_size:
    :param kernel:
    :param fr_value:
    :param bg_value:
    :param src_data:
    :return:
    """
    for _ in range(thr):
        src_data = gray_dilate(win_size, kernel, src_data)
    for _ in range(thr):
        src_data = gray_erode(win_size, kernel, src_data)
    return src_data


def sieve(in_file, dst_dir, th, op, co):
    # 定义结构元
    SE = {4: np.array([0, 1, 0, 1, 1, 1, 0, 1, 0]),
          8: np.array([1, 1, 1, 1, 1, 1, 1, 1, 1])}
    basename = os.path.splitext(os.path.basename(in_file))[0]
    dst_file = os.path.join(dst_dir, basename) + '_sieve.tif'
    if os.path.exists(dst_file):
        return None
    in_ds = gdal.Open(in_file)
    xsize = in_ds.RasterXSize
    ysize = in_ds.RasterYSize
    prj = in_ds.GetProjection()
    geo = in_ds.GetGeoTransform()
    srcband = in_ds.GetRasterBand(1)
    # 创建输出文件，存放经开运算和填孔洞后的结果
    drv = gdal.GetDriverByName('GTiff')
    dst_ds = drv.Create(dst_file, xsize, ysize, 1, gdal.GDT_Byte)
    dst_ds.SetProjection(prj)
    dst_ds.SetGeoTransform(geo)
    dstband = dst_ds.GetRasterBand(1)
    maskband = None
    result = gdal.SieveFilter(srcband, maskband, dstband,
                              th, co, callback=None)
    dstband.FlushCache()
    # 进行开操作，平滑边缘
    kernel = SE[co]
    win_size = np.sqrt(kernel.size)
    src_data = dstband.ReadAsArray()
    if not win_size % 1 == 0:
        raise ('The size of SE is wrong!')
    filter_img = opening(win_size, kernel, op, src_data)
    # 更新结果
    dstband.WriteArray(filter_img)
    dstband.FlushCache()
    in_ds = srcband = dst_ds = dstband = filter_img  = None
    return None


def main(in_dir, out_dir, threshold, open_num, connect):
    if os.path.isdir(in_dir):
        files = searchfiles(in_dir, partfileinfo='L2A_T50SKE_A021951_20190905T030727_class.tif')
    else:
        files = [in_dir]
    jobs = os.cpu_count() - 1 if os.cpu_count() < len(files) else len(files)
    pool = mp.Pool(processes=jobs)
    for ifile in files:
        pool.apply_async(sieve, args=(ifile, out_dir, threshold, open_num, connect))
    pool.close()
    pool.join()
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
    in_dir = r"\\192.168.0.234\nydsj\user\ZSS\2020qixian\class"
    out_dir = r"\\192.168.0.234\nydsj\user\ZSS\2020qixian\sieve"
    threshold = 3
    open_num = 1
    connectedness = 8
    main(in_dir, out_dir, threshold, open_num, connectedness)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
