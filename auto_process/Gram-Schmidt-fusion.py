#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/5/21 15:02
# @Author  : zhaoss
# @FileName: Gram-Schmidt-fusion.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import glob
import time
import numpy as np
import tempfile
import shutil
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def simulatedPan(mss_dataset):
    # 获取多光谱数据
    mss_arrays = mss_dataset.ReadAsArray()
    # 模拟低分辨率全色影像
    simulated_array = np.mean(mss_arrays, axis=0, dtype=np.uint16)
    # 创建输出影像
    simulated_pan_ds = gdal.GetDriverByName('MEM').Create("", mss_dataset.RasterXSize, mss_dataset.RasterYSize, 1,
                                                          gdal.GDT_UInt16)
    simulated_pan_ds.SetProjection(mss_dataset.GetProjection())
    simulated_pan_ds.SetGeoTransform(mss_dataset.GetGeoTransform())
    simulated_pan_ds.GetRasterBand(1).WriteArray(simulated_array)
    return simulated_pan_ds


def phi(mss_band, gst_band, mean):
    # 计算两个波段的协方差
    n_element = mss_band.shape[0] * mss_band.shape[1]
    gst_band_mean = np.mean(gst_band)
    cov = np.sum((mss_band - mean) * (gst_band - gst_band_mean)) / n_element
    # 计算gst_band的方差
    variance = np.sum((gst_band - gst_band_mean) ** 2) / n_element
    phi_value = cov / variance
    return phi_value


def Gram_Schmidt_Transform(simulated_pan_dataset, mss_dataset, GST_img_path):
    # 创建经GS变换后的矩阵
    xsize = mss_dataset.RasterXSize
    ysize = mss_dataset.RasterYSize
    bandcount = mss_dataset.RasterCount
    GST = np.zeros((bandcount, ysize, xsize), dtype=np.float32, order="C")
    # 第一分量保持不变
    GST[0, :, :] = simulated_pan_dataset.ReadAsArray()
    for iband in range(1, bandcount):
        mss_array = mss_dataset.GetRasterBand(iband + 1).ReadAsArray()
        mss_mean = np.mean(mss_array)
        for iGSband in range(iband):
            if iGSband == 0:
                phi_gs = phi(mss_array, GST[iGSband, :, :], mean=mss_mean) * GST[iGSband, :, :]
            else:
                phi_gs += phi(mss_array, GST[iGSband, :, :], mean=mss_mean) * GST[iGSband, :, :]
        GST[iband, :, :] = mss_array - mss_mean - phi_gs
    # 存储除第一分量之外的其它分量为影像
    tiff_driver = gdal.GetDriverByName("GTiff")
    GST_ds = tiff_driver.Create(GST_img_path, xsize, ysize, 3, gdal.GDT_Float32)
    for iGSTband in range(bandcount - 1):
        GST_ds.GetRasterBand(iGSTband + 1).WriteArray(GST[iGSTband + 1, :, :])
    GST_ds.FlushCache()
    GST_ds = None
    GST = None
    return None


def cal_hist(array):
    bin = np.arange(start=0, stop=int(array.max()) + 2, step=1)
    his, bins = np.histogram(array, bins=bin)
    # 计算累计直方图
    cdf = np.cumsum(his) / (array.shape[0] * array.shape[1])
    return cdf[:], bins[:-1]


# def histogram_match(pan_dataset, simulated_pan_dataset):
#     pan_arr = pan_dataset.ReadAsArray()
#     simulated_pan_arr = simulated_pan_dataset.ReadAsArray()
#     # 对高分辨率全色影像进行拉伸，使之具有和模拟全色相同的色阶
#     pan_min = pan_arr.min()
#     pan_max = pan_arr.max()
#     simu_pan_min = simulated_pan_arr.min()
#     simu_pan_max = simulated_pan_arr.max()
#     stretch_pan = simu_pan_min + (simu_pan_max - simu_pan_min) * ((pan_arr - pan_min) / (pan_max - pan_min))
#     # 对stretch_pan进行直方图均衡
#     # 求取stretch_pan的累计直方图
#     stretch_pan_his, stretch_pan_bins = cal_hist(stretch_pan)
#     # 对stretch_pan进行直方图均衡
#     stretch_pan_his_equ = np.round(stretch_pan_his * simulated_pan_arr.max())
#
#     return 1


def modify_pan_stat(pan_dataset, simulated_pan_dataset):
    img3 = simulated_pan_dataset.ReadAsArray()
    img1 = pan_dataset.ReadAsArray()
    mu3 = np.mean(img3)
    mu1 = np.mean(img1)
    # 计算pan的方差
    var1 = np.sum((img1 - mu1) ** 2) / (img1.shape[0] * img1.shape[1])
    # 计算simulated_pan的方差
    var3 = np.sum((img3 - mu3) ** 2) / (img3.shape[0] * img3.shape[1])
    sigma3 = np.sqrt(var3)
    sigma1 = np.sqrt(var1)
    gain = sigma3 / sigma1  # 增益
    print(gain)
    bias = mu3 - (gain * mu1)  # 偏移
    print(bias)
    M_P = img1 * gain + bias
    return M_P


def resize_tif(pan, mss):
    # 打开高分辨率影像
    pan_ds = gdal.Open(pan)
    pan_xsize = pan_ds.RasterXSize
    pan_ysize = pan_ds.RasterYSize
    pan_geo = pan_ds.GetGeoTransform()
    # 打开低分辨率影像
    mss_ds = gdal.Open(mss)
    mss_prj = mss_ds.GetProjection()
    mss_geo = mss_ds.GetGeoTransform()
    mss_xsize = mss_ds.RasterXSize
    mss_ysize = mss_ds.RasterYSize
    bandCount = mss_ds.RasterCount  # Band Count
    dataType = mss_ds.GetRasterBand(1).DataType  # Data Type
    # 判断输入影像是否正确
    if pan_geo[1] > mss_geo[1]:
        sys.exit("The order of input files is wrongT!")
    # 计算输出后影像的分辨率
    # 计算缩放系数
    fact = np.array([pan_xsize / mss_xsize, pan_ysize / mss_ysize])
    xs = mss_geo[1] / fact[0]
    ys = mss_geo[5] / fact[1]
    # 创建输出影像
    out_driver = gdal.GetDriverByName("MEM")
    out_ds = out_driver.Create('', pan_xsize, pan_ysize, bandCount, dataType)
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
    data = out_ds.ReadAsArray()
    in_band = out_ds.GetRasterBand(1)
    geotransform = out_ds.GetGeoTransform()
    projection = out_ds.GetProjection()
    pan_ds = None
    mss_ds = None
    out_ds = None
    return data, in_band, geotransform, projection


def main(pan, mss):
    # 支持中文路径
    gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
    # 注册所有gdal驱动
    gdal.AllRegister()
    # 打开栅格影像
    pan_ds = gdal.Open(pan)
    mss_ds = gdal.Open(mss)
    # 获取待处理影像的文件名
    pan_file_name = os.path.splitext(os.path.basename(pan))[0]
    # 获取系统临时文件的路径
    temp_dir = tempfile.gettempdir()
    # 创建本次处理时临时文件
    temp_directory = tempfile.mkdtemp(dir=temp_dir, prefix="GS_" + pan_file_name + "_")
    # 打开多光谱影像应以模拟低分辨率全色影像
    simulated_pan_ds = simulatedPan(mss_ds)
    # 进行GST变换
    GST_file_path = tempfile.mktemp(dir=temp_directory, prefix="GS_GST_without_GST1_", suffix=".tiff")
    Gram_Schmidt_Transform(simulated_pan_ds, mss_ds, GST_file_path)
    # 将高分辨率全色影像和模拟全色影像进行直方图匹配，使之和模拟全色影像具有相同的统计指数
    # modified_pan_ds = histogram_match(pan_ds, simulated_pan_ds)
    modified_pan_arr = modify_pan_stat(pan_ds, simulated_pan_ds)
    # 对GS变换后除第一分量的结果进行重采样，使其具有和高分全色一致的分辨率
    GST_resize_file = tempfile.mktemp(dir=temp_directory, prefix="GS_GST_resize_without_GST1_", suffix=".tiff")
    resize_tif()
    # 删除临时文件
    # shutil.rmtree(temp_directory)
    print(temp_directory)
    return None


if __name__ == '__main__':
    start_time = time.clock()
    in_pan_file = r"F:\test_data\GS_test\5952_pan.tif"
    in_mss_file = r"F:\test_data\GS_test\5952_MSS.tif"
    main(pan=in_pan_file, mss=in_mss_file)
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
