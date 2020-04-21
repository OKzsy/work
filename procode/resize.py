#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Author:zhaoss
Email:zhaoshaoshuai@hnnydsj.com
Create date:  
File: .py
Description:


Parameters


"""
import os
import sys
import glob
import gc
import numpy as np
import time
from osgeo import gdal, ogr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def resize(src_dst, dst_xsize, dst_ysize, seq):
    """
    根据输入的目标影像行列数对原始影像进行缩放，缩放方法为双线性插值
    :param src_dst: 原始数据集
    :param dst_xsize: 目标影像列数
    :param dst_ysize: 目标影像行数
    :return: 返回重采样后的目标影像数据集
    """
    # 获取原始影像的数据类型
    datatype = src_dst.GetRasterBand(1).DataType
    # 根据目标大小，在内存创建结果影像
    tmp_dst_path = r'/vsimem/tmp_dst_{}.tiff'.format(str(seq))
    gdal.Translate(tmp_dst_path, src_dst, resampleAlg=gdal.GRA_Bilinear, format='GTiff', width=dst_xsize,
                   height=dst_ysize, outputType=datatype)
    tmp_dst = gdal.Open(tmp_dst_path)
    src_dst = None
    gdal.Unlink(tmp_dst_path)
    gc.collect()
    return tmp_dst


def main(pan, mss, out):
    pan_ds = gdal.Open(pan)
    pan_xsize = pan_ds.RasterXSize
    pan_ysize = pan_ds.RasterYSize
    mss_ds = gdal.Open(mss)
    mss_prj = mss_ds.GetProjection()
    mss_geo = mss_ds.GetGeoTransform()
    mss_xsize = mss_ds.RasterXSize
    mss_ysize = mss_ds.RasterYSize
    bandCount = mss_ds.RasterCount  # Band Count
    dataType = mss_ds.GetRasterBand(1).DataType  # Data Type
    # 计算输出后影像的分辨率
    # 计算缩放系数
    fact = np.array([pan_xsize / mss_xsize, pan_ysize / mss_ysize])
    xs = mss_geo[1] / fact[0]
    ys = mss_geo[5] / fact[1]
    # 创建输出影像
    out_driver = gdal.GetDriverByName("GTiff")
    out_ds = out_driver.Create(out, pan_xsize, pan_ysize, bandCount, dataType)
    out_ds.SetProjection(mss_prj)
    out_geo = list(mss_geo)
    out_geo[1] = xs
    out_geo[5] = ys
    out_ds.SetGeoTransform(out_geo)
    # 执行重投影和重采样
    print('Begin to reprojection and resample!')
    res = gdal.ReprojectImage(mss_ds, out_ds, \
                              mss_prj, mss_prj, \
                              gdal.GRA_Bilinear, callback=progress)
    out_ds.FlushCache()
    pan_ds = None
    mss_ds = None
    out_ds = None

    return 1


if __name__ == '__main__':
    # 注册所有gdal的驱动
    gdal.AllRegister()
    gdal.SetConfigOption("gdal_FILENAME_IS_UTF8", "YES")

    start_time = time.time()
    pan_file = r"F:\test_data\new_test\GF2_20180718_L1A0003330812_sha_inter_ceil_num.tiff"
    mss_file = r"F:\test_data\new_test\GF2_20180718_L1A0003330812_sha.tiff"
    out_file = r"F:\test_data\new_test\GF2_20180718_L1A0003330812_sha_inter_gdal.tiff"

    main(pan_file, mss_file, out_file)

    end_time = time.time()

    print("time: %.4f secs." % (end_time - start_time))
