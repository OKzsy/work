#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2021/5/9 13:20
# @Author  : zhaoss
# @FileName: crop_drought.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import sys
import glob
import time
import fnmatch
import matplotlib.pyplot as plt
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def hist(data, ratio):
    bins = np.arange(start=int(data.min()), stop=int(data.max()) + 2, step=1)
    n, xbin = np.histogram(data, bins=bins)
    nozero_index = np.where(xbin[:-1] != 0)
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
    return min_gray[0], max_gray[0]


def curve(x, y, quantile=[0, 100]):
    x_q1, x_q3 = np.percentile(x, quantile)
    x_index = np.where((x >= x_q1) & (x <= x_q3))
    x = x[x_index]
    y = y[x_index]
    # 拟合方程
    x_mean = np.mean(x)
    y_mean = np.mean(y)
    # y = a + bx
    b = np.sum((x - x_mean) * (y - y_mean)) / np.sum((x - x_mean) * (x - x_mean))
    a = y_mean - b * x_mean
    forecast_y = a + b * x
    # 计算决定系数
    r2 = 1 - (np.sum((y - forecast_y) * (y - forecast_y)) / np.sum((y - y_mean) * (y - y_mean)))
    return a, b, r2


def data_clean(x, y, init_scale, init_offset, counter, m=10):
    m = counter * m
    # 数据剔除位置索引，保留为True, 剔除位置为False
    status_index = np.ones_like(x, dtype=np.bool_)
    status_count = 0
    # 数据分折统计
    unique_x = np.unique(x)
    unique_x[0] -= unique_x[0] * 0.1
    breakpoints = [value for value in range(0, len(unique_x), m)]
    breakpoints[-1] = len(unique_x)
    for k in range(len(breakpoints) - 1):
        sub_low_point = unique_x[breakpoints[k]]
        sub_high_point = unique_x[breakpoints[k + 1] - 1]
        sub_index = np.where((x > sub_low_point) & (x <= sub_high_point))
        sub_x = x[sub_index]
        sub_y = y[sub_index]
        # 拟合子集系数
        sub_offset, sub_scale, sub_coe_dete = curve(sub_x, sub_y)
        if (sub_offset != init_offset) | (sub_scale != init_scale):
            err = np.abs(sub_y - (sub_offset + sub_scale * sub_x))
            # 误差最大位置索引
            max_err_index = np.argmax(err)
            # 在原始数据中提出对应位置数据
            err_index = breakpoints[k] + max_err_index
            status_index[err_index] = False
            status_count += 1
    if (status_count == 0) | (m > len(x)):
        sub_x = x[status_index]
        sub_y = y[status_index]
        # 返回最终系数
        sub_offset, sub_scale, sub_coe_dete = curve(sub_x, sub_y)
        return sub_offset, sub_scale
    else:
        sub_x = x[status_index]
        sub_y = y[status_index]
        counter += 1
        coe = data_clean(sub_x, sub_y, init_scale, init_offset, counter)
    return coe


def coverage(red, nir):
    zero_index = np.where(red == 0)
    # 计算ndvi
    ndvi = ((nir - red) * 10000 / (nir + red + 0.00001)).astype(np.int16)
    # 统计最大最小值
    ndvi_min, ndvi_max = hist(ndvi, 1)
    ndvi = np.maximum(np.minimum(ndvi, ndvi_max), ndvi_min)
    cov = 1 - ((ndvi_max - ndvi) / (ndvi_max - ndvi_min)) ** 0.6175
    cov = np.minimum(cov, 0.99)
    return cov


def regression_equation(red, nir):
    x = []
    y = []
    # 去除背景
    tmp_red = red[np.where(red > 0)]
    red_unique = np.unique(tmp_red)
    # 针对大影像统计时采用间隔取样
    red_unique_num = tmp_red.size
    interval_base_num = 200000
    if red_unique_num > interval_base_num:
        step = int((red_unique_num / interval_base_num) ** 0.5)
    else:
        step = 1
    for i in range(0, len(red_unique), step):
        ired = red_unique[i]
        index = np.where(red == ired)
        tmp_nir = np.sort(nir[index])
        point_num = 1
        if tmp_nir.size >= point_num:
            tmp_nir = tmp_nir[:point_num]
        for inir in tmp_nir:
            x.append(ired)
            y.append(inir)
    x = np.array(x)
    y = np.array(y)
    # 确定初始回归方程
    scale = offset = coe_dete = 0
    quantiles = [[0, 25], [0, 50], [0, 75], [0, 100], [25, 50], [25, 75], [25, 100], [50, 75], [50, 100], [75, 100]]
    for k in range(len(quantiles)):
        tmp_quantile = quantiles[k]
        tmp_offset, tmp_scale, tmp_coe_dete = curve(x, y, tmp_quantile)
        if tmp_coe_dete > coe_dete:
            scale = tmp_scale
            offset = tmp_offset
            coe_dete = tmp_coe_dete
            quantile = tmp_quantile
    # 去除非土壤贡献点
    x_q1, x_q3 = np.percentile(x, quantile)
    x_index = np.where((x >= x_q1) & (x <= x_q3))
    x = x[x_index]
    y = y[x_index]
    counter = 1
    coe = data_clean(x, y, scale, offset, counter)
    return coe[1]


def main(src, dst):
    src_ds = gdal.Open(src)
    xsize = src_ds.RasterXSize
    ysize = src_ds.RasterYSize
    geo = src_ds.GetGeoTransform()
    prj = src_ds.GetProjection()
    # 获取数据
    red = src_ds.GetRasterBand(3).ReadAsArray() / 10000
    nir = src_ds.GetRasterBand(8).ReadAsArray() / 10000
    nodata_index = np.where(red == 0)
    # 确定M
    coe = regression_equation(red, nir)
    # 计算覆盖度
    cov = coverage(red, nir)
    print(coe)
    # coe = 1.060968
    mpdi = (red + coe * nir - cov * (0.05 + 0.5 * coe)) / ((1.0 - cov) * (coe * coe + 1) ** 0.5)
    mpdi = np.maximum(mpdi, 0.01)
    mpdi[nodata_index] = 0
    # 计算npdi
    mpdi = (mpdi * 10000).astype(np.int16)
    mpdi_min, mpdi_max = hist(mpdi, 1)
    mpdi = np.maximum(np.minimum(mpdi, mpdi_max), mpdi_min)
    npdi = (mpdi - mpdi_min) / (mpdi_max - mpdi_min)
    npdi = np.maximum(npdi, 0.0001)
    npdi[nodata_index] = 0
    drv = gdal.GetDriverByName('GTiff')
    dst_ds = drv.Create(dst, xsize, ysize, 1, gdal.GDT_Float32)
    dst_ds.SetGeoTransform(geo)
    dst_ds.SetProjection(prj)
    dst_ds.GetRasterBand(1).WriteArray(npdi)

    src_ds = cov_ds = dst_ds = None

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
    src_file = r"\\192.168.0.234\nydsj\project\40.长垣高标准农田\1.data\3.S2\2.atm\2022年\9月\L2A_T50SKD_A037967_20220929T031313_ref_10m.tif"
    dst_file = r"F:\test\drought\L2A_T50SKD_A037967_20220929T031313_dr.tif"
    main(src_file, dst_file)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
