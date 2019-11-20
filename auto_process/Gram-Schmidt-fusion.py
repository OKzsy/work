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
import sys
import glob
import gc
import math
import time
import numpy as np
import tempfile
import shutil
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def simulatedPan(mss_resize_file, coordinate):
    # 获取多光谱数据
    mss_dataset = gdal.Open(mss_resize_file)
    # 获取有效数据区域
    offset = geo_to_corner(coordinate, mss_dataset)
    mss_arrays = mss_dataset.ReadAsArray(offset[0], offset[1], coordinate[2], coordinate[3])
    zero_index = np.where(mss_arrays[0, :, :] == 0)
    zero_count = zero_index[0].shape[0]
    # 模拟低分辨率全色影像
    simulated_array = np.mean(mss_arrays, axis=0, dtype=np.uint16)
    # 创建输出影像
    simulated_pan_ds = gdal.GetDriverByName('MEM').Create("", coordinate[2], coordinate[3], 1,
                                                          gdal.GDT_UInt16)
    simulated_pan_ds.SetProjection(mss_dataset.GetProjection())
    simulated_pan_geo = list(mss_dataset.GetGeoTransform())
    simulated_pan_geo[0] = coordinate[0]
    simulated_pan_geo[3] = coordinate[1]
    simulated_pan_ds.SetGeoTransform(simulated_pan_geo)
    simulated_pan_ds.GetRasterBand(1).WriteArray(simulated_array)
    return simulated_pan_ds, zero_index, zero_count


def phi(mss_band, gst_band, zero_num, mean):
    mss_zero_num = np.where(np.isnan(mss_band))[0].shape[0]
    gst_zero_num = np.where(np.isnan(gst_band))[0].shape[0]
    zero_num = max(mss_zero_num, gst_zero_num)
    # 计算两个波段的协方差
    n_element = mss_band.shape[0] * mss_band.shape[1] - zero_num
    gst_band_mean = np.nanmean(gst_band)
    cov = np.nansum((mss_band - mean) * (gst_band - gst_band_mean)) / n_element
    # 计算gst_band的方差
    variance = np.nansum((gst_band - gst_band_mean) ** 2) / n_element
    phi_value = cov / variance
    return phi_value


def Gram_Schmidt_Transform(simulated_pan_dataset, mss_resize_file, coordinate, zero_index, zero_number, GST_img_path):
    # 创建经GS变换后的矩阵
    xsize = simulated_pan_dataset.RasterXSize
    ysize = simulated_pan_dataset.RasterYSize
    simulateed_pan_prj = simulated_pan_dataset.GetProjection()
    simulateed_pan_geo = simulated_pan_dataset.GetGeoTransform()
    mss_dataset = gdal.Open(mss_resize_file)
    # 获取有效数据区域
    offset = geo_to_corner(coordinate, mss_dataset)
    bandcount = mss_dataset.RasterCount + 1
    GST = np.zeros((bandcount, ysize, xsize), dtype=np.float32, order="C")
    # 第一分量保持不变
    simulated_pan_array = simulated_pan_dataset.ReadAsArray().astype(np.float32)
    simulated_pan_array[zero_index] = np.nan
    for iband in range(1, bandcount):
        mss_array = mss_dataset.GetRasterBand(iband).ReadAsArray(offset[0], offset[1], coordinate[2],
                                                                 coordinate[3]).astype(np.float32)
        mss_array[zero_index] = np.nan
        mss_mean = np.nanmean(mss_array)
        for iGSband in range(iband):
            if iGSband == 0:
                phi_gs = phi(mss_array, simulated_pan_array, zero_number, mean=mss_mean) * simulated_pan_array
            else:
                phi_gs += phi(mss_array, GST[iGSband, :, :], zero_number, mean=mss_mean) * GST[iGSband, :, :]
        GST[iband, :, :] = mss_array - mss_mean - phi_gs
    # 存储除第一分量之外的其它分量为影像
    tiff_driver = gdal.GetDriverByName("GTiff")
    GST_ds = tiff_driver.Create(GST_img_path, xsize, ysize, bandcount - 1, gdal.GDT_Int16)
    GST_ds.SetProjection(simulateed_pan_prj)
    GST_ds.SetGeoTransform(simulateed_pan_geo)
    for iGSTband in range(bandcount - 1):
        GST_ds.GetRasterBand(iGSTband + 1).WriteArray(GST[iGSTband + 1, :, :].astype(np.int16))
    GST_ds.FlushCache()
    GST_ds = None
    GST = None
    return None


def img_stretch(ori_image_data, std_img):
    ori_min = ori_image_data.min()
    ori_max = ori_image_data.max()
    std_min = std_img.min()
    std_max = std_img.max()
    stretch_ori = std_min + (std_max - std_min) * ((ori_image_data - ori_min) / (ori_max - ori_min))
    return stretch_ori.astype(np.uint16)


def histogram_equalization(data):
    # 获取图像中灰度级范围
    bins = np.arange(start=1, stop=int(data.max()) + 2, step=1)
    n, xbin = np.histogram(data, bins=bins)
    zero_index = np.where(data == 0)
    # 计算累计直方图
    cdf = np.cumsum(n) / (data.shape[0] * data.shape[1] - zero_index[0].shape[0])
    return cdf[:], xbin[:-1]


def match(ori_image_ds, std_img_ds, coordinate):
    # 获取数据的有效区域
    offset = geo_to_corner(coordinate, ori_image_ds)
    ori_image_data = ori_image_ds.ReadAsArray(offset[0], offset[1], coordinate[2], coordinate[3])
    std_img = std_img_ds.ReadAsArray()
    ori_image_data = img_stretch(ori_image_data, std_img)
    ori_cdf, ori_bins = histogram_equalization(ori_image_data)
    # 打开标准影像进行直方图均衡
    std_cdf, std_bins = histogram_equalization(std_img)
    std_img = None
    img_eq_array = np.zeros_like(ori_image_data, dtype=np.uint16)
    # 处理原始影像
    for ivalue in ori_bins:
        # 计算原始和标准之间的差异
        diff = np.abs(ori_cdf[ivalue - 1] - std_cdf)
        index = np.where(diff == diff.min())
        res_index = np.where(ori_image_data == ivalue)
        img_eq_array[res_index] = index[0][0]
        print("ivalue: {}, new_value: {}".format(ivalue, index[0][0]))
    ori_image_data = None
    gc.collect()
    return img_eq_array


def modify_pan_stat(pan_dataset, simulated_pan_dataset, coordinate, index, zero_number):
    simulated_array = simulated_pan_dataset.ReadAsArray()
    simulated_array = np.where(simulated_array == 0, np.nan, simulated_array)
    offset = geo_to_corner(coordinate, pan_dataset)
    pan_array = pan_dataset.ReadAsArray(offset[0], offset[1], coordinate[2], coordinate[3])
    pan_array[index] = 0
    pan_array = np.where(pan_array == 0, np.nan, pan_array)
    simu_mean = np.nanmean(simulated_array)
    pan_mean = np.nanmean(pan_array)
    # 计算pan的方差
    pan_var = np.nansum((pan_array - pan_mean) ** 2) / (coordinate[2] * coordinate[3] - zero_number)
    # 计算simulated_pan的方差
    simu_var = np.nansum((simulated_array - simu_mean) ** 2) / (coordinate[2] * coordinate[3] - zero_number)
    simu_sigma = np.sqrt(simu_var)
    pan_sigma = np.sqrt(pan_var)
    gain = simu_sigma / pan_sigma  # 增益
    bias = simu_mean - (gain * pan_mean)  # 偏移
    M_P = pan_array * gain + bias
    return M_P.astype(np.float32)


def resize_tif(pan_ds, mss_ds, GS_mss_resize_path):
    # 打开高分辨率影像
    pan_geo = pan_ds.GetGeoTransform()
    # 打开低分辨率影像
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
    fact = np.array([pan_geo[1] / mss_geo[1], pan_geo[5] / mss_geo[5]])
    new_xsize = math.ceil(mss_xsize / fact[0])
    new_ysize = math.ceil(mss_ysize / fact[1])
    # 创建输出影像
    out_driver = gdal.GetDriverByName("GTiff")
    out_ds = out_driver.Create(GS_mss_resize_path, new_xsize, new_ysize, bandCount, dataType)
    out_ds.SetProjection(mss_prj)
    out_geo = list(mss_geo)
    out_geo[1] = pan_geo[1]
    out_geo[5] = pan_geo[5]
    out_ds.SetGeoTransform(out_geo)
    # 执行重投影和重采样
    print('Begin to reprojection and resample!')
    res = gdal.ReprojectImage(mss_ds, out_ds, \
                              mss_prj, mss_prj, \
                              gdal.GRA_NearestNeighbour, callback=progress)
    out_ds = None
    return None


def Inv_Gram_Schmidt_Transform(modified_pan, GST_file, mss_resize_file, coordinate, index, zero_num, fusion):
    # 创建经GST逆变换后的矩阵
    GST_ds = gdal.Open(GST_file)
    GST_prj = GST_ds.GetProjection()
    GST_geo = GST_ds.GetGeoTransform()
    xsize = GST_ds.RasterXSize
    ysize = GST_ds.RasterYSize
    bandcount = GST_ds.RasterCount + 1
    # 创建融合后的影像
    driver = gdal.GetDriverByName("GTiff")
    fusion_ds = driver.Create(fusion, xsize, ysize, bandcount - 1, gdal.GDT_UInt16)
    fusion_ds.SetProjection(GST_prj)
    fusion_ds.SetGeoTransform(GST_geo)
    # 第一分量保持不变
    GST_array = GST_ds.ReadAsArray().astype(np.float32)
    mss_resize_ds = gdal.Open(mss_resize_file)
    # 获取数据的有效区域
    offset = geo_to_corner(coordinate, mss_resize_ds)
    for iband in range(1, bandcount):
        mss_resize_array = mss_resize_ds.GetRasterBand(iband).ReadAsArray(offset[0], offset[1], coordinate[2],
                                                                          coordinate[3])
        mss_resize_array = np.where(mss_resize_array == 0, np.nan, mss_resize_array)
        mss_resize_mean = np.nanmean(mss_resize_array)
        for iGSband in range(iband):
            if iGSband == 0:
                phi_gs = phi(mss_resize_array, modified_pan, zero_num,
                             mean=mss_resize_mean) * modified_pan  # 在这要求原始多光谱必须为高分辨率
            else:
                GST_array[iGSband - 1, :, :][index] = np.nan
                temp_GST_arr = GST_array[iGSband - 1, :, :]
                phi_gs += phi(mss_resize_array, temp_GST_arr, zero_num, mean=mss_resize_mean) * temp_GST_arr
        GST_inv = GST_array[iband - 1, :, :] + mss_resize_mean + phi_gs
        temp_arr = GST_inv - np.nanmean(GST_inv) + mss_resize_mean
        nan_index = np.where(np.isnan(temp_arr))
        temp_arr[nan_index] = 0
        temp_arr = np.maximum(temp_arr, 0).astype(np.uint16)
        fusion_ds.GetRasterBand(iband).WriteArray(temp_arr)
    fusion_ds.FlushCache()
    fusion_ds = None
    return None


def geo_to_corner(point_coor, dateset):
    # 获取栅格的放射变换参数
    raster_geo = dateset.GetGeoTransform()
    # 计算逆放射变换系数
    raster_inv_geo = gdal.InvGeoTransform(raster_geo)
    off_ulx, off_uly = map(round, gdal.ApplyGeoTransform(raster_inv_geo, point_coor[0], point_coor[1]))
    return off_ulx, off_uly


def corner_to_geo(sample, line, dataset):
    # 计算指定行,列号的地理坐标
    Geo_t = dataset.GetGeoTransform()
    # 计算地理坐标
    geoX = Geo_t[0] + sample * Geo_t[1]
    geoY = Geo_t[3] + line * Geo_t[5]
    return geoX, geoY


def min_rect(pan_ds, mss_file):
    # 打开重采样后的多光谱影像，获取其左上和右下交点坐标
    mss_ds = gdal.Open(mss_file)
    mss_xsize = mss_ds.RasterXSize
    mss_ysize = mss_ds.RasterYSize
    mss_ulx, mss_uly = corner_to_geo(0, 0, mss_ds)
    mss_drx, mss_dry = corner_to_geo(mss_xsize, mss_ysize, mss_ds)
    # 获取全色影像的左上和右下交点坐标
    pan_geo = pan_ds.GetGeoTransform()
    pan_xsize = pan_ds.RasterXSize
    pan_ysize = pan_ds.RasterYSize
    pan_ulx, pan_uly = corner_to_geo(0, 0, pan_ds)
    pan_drx, pan_dry = corner_to_geo(pan_xsize, pan_ysize, pan_ds)
    # 计算最小重叠区域交点坐标
    ulx = max(pan_ulx, mss_ulx)
    uly = min(pan_uly, mss_uly)
    drx = min(pan_drx, mss_drx)
    dry = max(pan_dry, mss_dry)
    # 计算重叠的行列数
    col = round((drx - ulx) / pan_geo[1])
    raw = round((dry - uly) / pan_geo[5])
    return [ulx, uly, col, raw]


def main(pan, mss, fusion):
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
    # 对多光谱进行重采样，使其和全色具有相同的行列号
    print(time.clock())
    mss_resize_file = tempfile.mktemp(dir=temp_directory, prefix="GS_mss_resize_", suffix=".tiff")
    resize_tif(pan_ds, mss_ds, mss_resize_file)

    # 计算全色和重采样后多光谱的最小重叠矩形
    coordinate = min_rect(pan_ds, mss_resize_file)
    mss_ds = None
    # 打开多光谱影像应以模拟低分辨率全色影像
    print(time.clock())
    simulated_pan_ds, zero_index, zero_count = simulatedPan(mss_resize_file, coordinate)

    # 进行GST变换
    print(time.clock())
    gc.collect()
    GST_file_path = tempfile.mktemp(dir=temp_directory, prefix="GS_GST_without_GST1_", suffix=".tiff")
    Gram_Schmidt_Transform(simulated_pan_ds, mss_resize_file, coordinate, zero_index, zero_count, GST_file_path)

    # 将高分辨率全色影像和模拟全色影像进行直方图匹配，使之和模拟全色影像具有相同的统计指数
    # modified_pan_arr = match(pan_ds, simulated_pan_ds, coordinate)
    print(time.clock())
    modified_pan_arr = modify_pan_stat(pan_ds, simulated_pan_ds, coordinate, zero_index, zero_number=zero_count)
    pan_ds = None

    # 进行GST逆变换Inv_Gram_Schmidt_Transform
    print(time.clock())
    gc.collect()
    Inv_Gram_Schmidt_Transform(modified_pan_arr, GST_file_path, mss_resize_file, coordinate, zero_index, zero_count,
                               fusion)
    # 删除临时文件
    # shutil.rmtree(temp_directory)
    print(temp_directory)
    return None


if __name__ == '__main__':
    start_time = time.clock()
    in_pan_file = r"F:\test_data\GS_test\GF2_PMS2_E114.0_N32.2_20180718_L1A0003330812-PAN2_atm.tiff"
    in_mss_file = r"F:\test_data\GS_test\GF2_PMS2_E114.0_N32.2_20180718_L1A0003330812-MSS2_atm.tiff"
    fusion_path = r"F:\test_data\GS_test\GF2_PMS2_E114.0_N32.2_20180718_L1A0003330812-py_sha.tif"
    # in_pan_file = r"F:\test_data\GS_test\3988007-PAN2-pian.tiff"
    # in_mss_file = r"F:\test_data\GS_test\3988007-MSS2-pian.tiff"
    # fusion_path = r"F:\test_data\GS_test\3988007-MSS2-pian_sha5.tif"
    main(pan=in_pan_file, mss=in_mss_file, fusion=fusion_path)
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
