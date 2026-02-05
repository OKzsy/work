#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/4/23 10:55
# @Author  : zhaoss
# @FileName: imgtobyte.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
对输入的影像采用2%线性拉伸，转换为可以在线展示的影像(Data_type:Byte,img_type:Tiff)
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
import numba as nb
from numba import njit, prange
from osgeo import gdal, ogr, osr, gdalconst
import gc

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def searchfiles(dirpath, partfileinfo="*", recursive=False):
    """列出符合条件的文件(包含路径)，默认不进行递归查询，当recursive为True时同时查询子文件夹"""
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


# 寻找输入数组的最大值和最小值, 兼容一维和二维数组, 返回结果是np.nan时表示错误
@njit(parallel=True, cache=True)
def get_min_max(matrix):
    a_min = a_max = np.nan
    if matrix.ndim == 1:
        rows = matrix.shape[0]
        a_min = a_max = matrix[0]
        for irow in prange(rows):
            ele = matrix[irow]
            a_min = min(a_min, ele)
            a_max = max(a_max, ele)
    elif matrix.ndim == 2:
        rows, cols = matrix.shape
        a_min = a_max = matrix[0, 0]
        for irow in prange(rows):
            for icol in range(cols):
                ele = matrix[irow, icol]
                a_min = min(a_min, ele)
                a_max = max(a_max, ele)
    return a_min, a_max


# 计算直方图, 兼容一/二维数组
@njit()
def calc_hist(matrix, step=None, bins=None):
    """
    针对非指定bins的情况，即利用step进行计算直方图，利用step进行计算在遥感图像
    处理中存在着物理意义。未来和numpy的histogram函数匹配，可以通过xbins[-2] += xbins[-1]
    输出xbins[:-1], bins_edge[:-2]来实现匹配
    """
    # 获取矩阵的最小值和最大值,用于计算bins_edge
    a_min, a_max = get_min_max(matrix)
    # 指定step和指定bins是两种情况，指定bins时需要将最后两个统计值合并在输出
    interval_length = a_max - a_min
    if step is None:
        if bins is None:
            step = 1
            bins_num = int(np.ceil((interval_length + step - 1) / step)) + 1
        else:
            step = interval_length / (bins + 1e-10)
            bins_num = (
                int(np.ceil((interval_length + step - 1) / step))
                if bins is None
                else bins
            )
    else:
        bins_num = int(np.ceil((interval_length + step - 1) / step)) + 1
    bins_edge_num = bins_num + 1
    bins_edge = np.zeros((bins_edge_num,), dtype=np.float64)
    for i in range(bins_edge_num):
        bins_edge[i] = a_min + i * step
    bins_edge[-1] = a_max
    # 计算直方图
    xbins = np.zeros((bins_num,), dtype=np.int64)
    zero_count = 0
    if matrix.ndim == 1:
        rows = matrix.shape[0]
        for irow in range(rows):
            ele = matrix[irow]
            if ele == 0:
                zero_count += 1
            if ele == a_max:
                idx = bins_num - 1
            else:
                idx = int((ele - a_min) / step)
            xbins[idx] += 1
    else:
        rows, cols = matrix.shape
        for irow in range(rows):
            for icol in range(cols):
                ele = matrix[irow, icol]
                if ele == 0:
                    zero_count += 1
                if ele == a_max:
                    idx = bins_num - 1
                else:
                    idx = int((matrix[irow, icol] - a_min) / step)
                xbins[idx] += 1
    return xbins, bins_edge, zero_count


def get_fast_where_parallel():
    # 使用极值作为默认参数
    # 在 Numba 标量计算中，value <= -np.inf 永远为 False
    @nb.vectorize(nopython=True)
    def fast_where(value, low_limit, upper_limit):
        # 确定拉伸后的范围
        low = 1
        high = 255
        if value <= low_limit:
            return low
        elif value >= upper_limit:
            return high
        else:
            return low + (high - low) * 1.0 * (value - low_limit) / (
                upper_limit - low_limit
            )

    @njit(parallel=True)
    def parallel_fast_where(matrix, low_limit=None, upper_limit=None):

        return fast_where(matrix, low_limit, upper_limit)

    return parallel_fast_where


def hist(data, ratio):
    n, xbin, zero_num = calc_hist(data, step=1)
    nozero_index = np.where(xbin[:-1] != 0)
    n = n[nozero_index]
    xbin = xbin[nozero_index]
    # 计算累计频率
    cdf = np.cumsum(n) / (data.size - zero_num)
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
    # gray = [[40, 179], [60, 198], [54, 218]]
    # min_gray = gray[band_index][0]
    # max_gray = gray[band_index][1]
    # 将直方图中ratio以外的值统一为min_gray和max_gray
    stretch_func = get_fast_where_parallel()
    stretched_img = stretch_func(band_data, min_gray[0], max_gray[0])
    # 反填背景值
    stretched_img[zero_index] = 0
    return stretched_img


def main(in_dir, out_dir, partfileinfo="*"):
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
        stretched_img_name = basename + "_strect4.tiff"
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
        tiff_driver = gdal.GetDriverByName("GTiff")
        stretched_ds = tiff_driver.Create(
            stretched_img_path, xsize, ysize, Bandcount, gdal.GDT_Byte
        )
        stretched_ds.SetProjection(data_ds.GetProjection())
        stretched_ds.SetGeoTransform(data_ds.GetGeoTransform())
        # 循环波段拉伸处理
        for iband in range(Bandcount):
            print("Start outputting the {0} band".format(iband + 1))
            stretched_band = Liner(data_ds, iband)
            stretched_ds.GetRasterBand(Bandcount - iband).WriteArray(
                stretched_band, callback=progress
            )
            stretched_band = None
            gc.collect()
        data_ds = None
        stretched_ds = None
    return None


if __name__ == "__main__":
    # 支持中文路径
    gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
    # 注册所有gdal驱动
    gdal.AllRegister()
    start_time = time.time()
    in_path = r"E:\data\gs"
    out_path = r"E:\data\gs\rgb"
    partfileinfo = "*L1A14469114001_sub.tif"
    main(in_path, out_path, partfileinfo=partfileinfo)
    end_time = time.time()

    print("time: %.4f secs." % (end_time - start_time))
