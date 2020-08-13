#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/6/18 14:40
# @Author  : zhaoss
# @FileName: Gram_Schimide_like_envi.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import sys
import glob
import gc
import math
import fnmatch
import time
import numpy as np
import numexpr as ne
import tempfile
import shutil
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def simulatedPan(mss_dataset, coordinate):
    # 获取数据有效区域
    offset = geo_to_corner(coordinate, mss_dataset)
    # 获取有效数据区域
    mss_arrays = mss_dataset.ReadAsArray(offset[0], offset[1], coordinate[4], coordinate[5])
    # xsize = mss_dataset.RasterXSize
    # ysize = mss_dataset.RasterYSize
    # 模拟低分辨率全色影像
    simulated_array = np.mean(mss_arrays, axis=0, dtype=np.uint16)
    # 创建输出影像
    simulated_pan_ds = gdal.GetDriverByName('MEM').Create("", coordinate[4], coordinate[5], 1,
                                                          gdal.GDT_UInt16)
    simulated_pan_ds.SetProjection(mss_dataset.GetProjection())
    simulated_pan_ds.SetGeoTransform(mss_dataset.GetGeoTransform())
    simulated_pan_ds.GetRasterBand(1).WriteArray(simulated_array)
    mss_arrays = None
    simulated_array = None
    return simulated_pan_ds


def phi(mss_band, gst_band, mean):
    # 计算两个波段的协方差
    n_elements = mss_band.size
    gst_band_mean = np.mean(gst_band, dtype=np.float64)
    mss_band = ne.evaluate("(mss_band - mean) * (gst_band - gst_band_mean)")
    # mss_band = (mss_band - mean) * (gst_band - gst_band_mean)
    cov = np.sum(mss_band, dtype=np.float64) / n_elements
    mss_band = None
    # 计算gst_band的方差
    variance = np.std(gst_band, dtype=np.float64) ** 2
    phi_value = cov / variance
    gst_band = None
    return phi_value


def Gram_Schmidt_Transform(simulated_pan_dataset, mss_dataset, coordinate, GST_img_path):
    # 获取数据有效区域
    offset = geo_to_corner(coordinate, mss_dataset)
    # 创建经GS变换后的矩阵
    xsize = simulated_pan_dataset.RasterXSize
    ysize = simulated_pan_dataset.RasterYSize
    simulateed_pan_prj = simulated_pan_dataset.GetProjection()
    simulateed_pan_geo = simulated_pan_dataset.GetGeoTransform()
    # 获取有效数据区域
    bandcount = mss_dataset.RasterCount + 1
    GST = np.zeros((bandcount - 1, ysize, xsize), dtype=np.float64, order="C")
    # 第一分量保持不变
    simulated_pan_array = simulated_pan_dataset.ReadAsArray()
    # 保存融合系数
    transform_cofficient = np.zeros((bandcount, bandcount-1), dtype=np.float64)
    for iband in range(1, bandcount):
        mss_array = mss_dataset.GetRasterBand(iband).ReadAsArray(offset[0], offset[1], coordinate[4], coordinate[5])
        mss_mean = np.mean(mss_array, dtype=np.float64)
        transform_cofficient[0, iband - 1] = mss_mean
        for iGSband in range(iband):
            if iGSband == 0:
                cofficient = phi(mss_array, simulated_pan_array, mean=mss_mean)
                phi_gs = ne.evaluate("cofficient * simulated_pan_array")
                # phi_gs = cofficient * simulated_pan_array
                transform_cofficient[iband, iGSband] = cofficient
            else:
                cofficient = phi(mss_array, GST[iGSband - 1, :, :], mean=mss_mean)
                temp_GST_arr = GST[iGSband - 1, :, :]
                ne.evaluate("cofficient * temp_GST_arr + phi_gs", out=phi_gs)
                # phi_gs += cofficient * GST[iGSband - 1, :, :]
                transform_cofficient[iband, iGSband] = cofficient
        # GST[iband - 1, :, :] = mss_array - mss_mean - phi_gs
        GST[iband - 1, :, :] = ne.evaluate("mss_array - mss_mean - phi_gs")
    mss_array = None
    simulated_pan_array = None
    # 存储除第一分量之外的其它分量为影像
    tiff_driver = gdal.GetDriverByName("GTiff")
    GST_ds = tiff_driver.Create(GST_img_path, xsize, ysize, bandcount - 1, gdal.GDT_Float32)
    GST_ds.SetProjection(simulateed_pan_prj)
    GST_ds.SetGeoTransform(simulateed_pan_geo)
    for iGSTband in range(bandcount - 1):
        GST_ds.GetRasterBand(iGSTband + 1).WriteArray(GST[iGSTband, :, :])
    GST_ds.FlushCache()
    GST_ds = None
    GST = None
    return transform_cofficient


def modify_pan_stat(pan_dataset, simulated_pan_dataset, coordinate):
    # 获取数据有效区域
    offset = geo_to_corner(coordinate, pan_dataset)
    pan_array = pan_dataset.ReadAsArray(offset[0], offset[1], coordinate[2], coordinate[3])
    # 增加获取多波段的无效值,按照全色进行重采样后获取
    # pan_geo = pan_dataset.GetGeoTransform()
    # simulated_array = simulated_pan_dataset.ReadAsArray()
    tmp_simulate_path = r'/vsimem/tmp_dst_simulate.tif'
    resize_tif(pan_dataset, simulated_pan_dataset, tmp_simulate_path)
    tmp_dst = gdal.Open(tmp_simulate_path)
    gdal.Unlink(tmp_simulate_path)
    gc.collect()
    # 获取模拟全色的有效数据区域
    offset = geo_to_corner(coordinate, tmp_dst)
    simulated_array = tmp_dst.ReadAsArray(offset[0], offset[1], coordinate[4], coordinate[5])
    tmp_pan_mss_arr = np.logical_and(pan_array, simulated_array)
    zero_index = np.where(tmp_pan_mss_arr == 0)

    simu_mean = np.mean(simulated_array, dtype=np.float64)
    pan_mean = np.mean(pan_array, dtype=np.float64)
    simu_sigma = np.std(simulated_array, dtype=np.float64)
    pan_sigma = np.std(pan_array, dtype=np.float64)

    gain = simu_sigma / pan_sigma  # 增益
    bias = simu_mean - (gain * pan_mean)  # 偏移
    M_P = pan_array * gain + bias
    simulated_array = None
    pan_array = None
    return M_P, zero_index


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
    res = gdal.ReprojectImage(mss_ds, out_ds, \
                              mss_prj, mss_prj, \
                              gdal.GRA_Bilinear, callback=progress)
    out_ds = None
    return None


def Inv_Gram_Schmidt_Transform(modified_pan, GST_resize_file, trans_coffic, coordinate, zero_index, fusion):
    # 获取数据的有效区域
    GST_ds = gdal.Open(GST_resize_file)
    offset = geo_to_corner(coordinate, GST_ds)
    # 创建经GST逆变换后的矩阵
    GST_prj = GST_ds.GetProjection()
    GST_geo = GST_ds.GetGeoTransform()
    bandcount = GST_ds.RasterCount + 1
    # 创建融合后的影像
    driver = gdal.GetDriverByName("GTiff")
    fusion_ds = driver.Create(fusion, coordinate[2], coordinate[3], bandcount - 1, gdal.GDT_UInt16)
    fusion_ds.SetProjection(GST_prj)
    out_geo = list(GST_geo)
    out_geo[0] = coordinate[0]
    out_geo[3] = coordinate[1]
    fusion_ds.SetGeoTransform(out_geo)
    # 第一分量保持不变
    # GST_array = GST_ds.ReadAsArray(offset[0], offset[1], coordinate[2], coordinate[3])
    for iband in range(1, bandcount):
        for iGSband in range(iband):
            if iGSband == 0:
                coffice = trans_coffic[iband, iGSband]
                phi_gs = ne.evaluate("coffice * modified_pan")
            else:
                # temp_GST_arr = GST_array[iGSband - 1, :, :]
                temp_GST_arr = GST_ds.GetRasterBand(iGSband).ReadAsArray(offset[0], offset[1], coordinate[2],
                                                                         coordinate[3])
                coffice = trans_coffic[iband, iGSband]
                ne.evaluate("coffice * temp_GST_arr + phi_gs", out=phi_gs)
                temp_GST_arr = None
        # GST_inv = GST_array[iband - 1, :, :] + trans_coffic[0, iband - 1] + phi_gs
        GST_inv = GST_ds.GetRasterBand(iband).ReadAsArray(offset[0], offset[1], coordinate[2], coordinate[3]) + \
                  trans_coffic[0, iband - 1] + phi_gs
        temp_arr = np.maximum(GST_inv, 0).astype(np.uint16)
        GST_inv = None
        gc.collect()
        temp_arr[zero_index] = 0
        print("Start outputting the fusion result of the {} band!".format(iband), flush=True)
        fusion_ds.GetRasterBand(iband).WriteArray(temp_arr, callback=progress)
        temp_arr = None
        gc.collect()
    fusion_ds.FlushCache()
    fusion_ds = None
    GST_ds = None
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
    mss_geo = mss_ds.GetGeoTransform()
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
    # 计算重叠的全色行列数
    pan_col = round((drx - ulx) / pan_geo[1])
    pan_row = round((dry - uly) / pan_geo[5])
    # 计算重叠的多光谱行列数
    mss_col = round((drx - ulx) / mss_geo[1])
    mss_row = round((dry - uly) / mss_geo[5])
    return [ulx, uly, pan_col, pan_row, mss_col, mss_row]


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


def main(in_dir, out_dir, partfileinfo=None):
    if partfileinfo == None:
        partfileinfo = "*MSS*atm.tif"
    # 支持中文路径
    gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
    # 注册所有gdal驱动
    gdal.AllRegister()
    # 递归搜寻需要处理的影像
    mss_files = searchfiles(in_dir, partfileinfo=partfileinfo, recursive=True)
    count = 1
    # 定义临时文件的路径
    temp_dir = os.path.join(out_dir, 'Temp')
    for mss in mss_files:
        print("A total of {} scene images, this is the {}".format(len(mss_files), count), flush=True)
        count += 1
        mss_basenames = os.path.basename(mss).split("_")
        img_id = mss_basenames[5].split("-")[0]
        pan = searchfiles(in_dir, partfileinfo='*' + img_id + '-PAN*.tif', recursive=True)[0]
        fusion_name = '_'.join([mss_basenames[0], mss_basenames[4], img_id])
        fusion = os.path.join(out_dir, fusion_name) + "_sha.tif"
        if os.path.exists(fusion):
            continue
        # 打开栅格影像
        pan_ds = gdal.Open(pan)
        mss_ds = gdal.Open(mss)
        # 判断全色和多光谱影像的投影是否一致，不一致退出程序
        pan_rpj = pan_ds.GetProjection()
        mss_rpj = mss_ds.GetProjection()
        pan_osr = osr.SpatialReference()
        pan_osr.ImportFromWkt(pan_rpj)
        mss_osr = osr.SpatialReference()
        mss_osr.ImportFromWkt(mss_rpj)
        if not pan_osr.IsSame(mss_osr):
            pan_ds = mss_ds = None
            sys.exit("The Projection is not same!")
        # 获取待处理影像的文件名
        pan_file_name = os.path.splitext(os.path.basename(pan))[0]
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        # 创建本次处理时临时文件
        temp_directory = tempfile.mkdtemp(dir=temp_dir, prefix="GS_" + pan_file_name + "_")
        # 获取全色和原始多光谱的最小重叠矩形
        coordinate = min_rect(pan_ds, mss)
        # 打开多光谱影像应以模拟低分辨率全色影像
        simulated_pan_ds = simulatedPan(mss_ds, coordinate)
        # 进行GST变换
        gc.collect()
        GST_file_path = tempfile.mktemp(dir=temp_directory, prefix="GS_GST_without_GST1_", suffix=".tiff")
        transform_cofficient = Gram_Schmidt_Transform(simulated_pan_ds, mss_ds, coordinate, GST_file_path)
        mss_ds = None
        gc.collect()
        # 对GST变换后的分量进行重采样，使其具有和全色相同的分辨率
        GST_resize_file = tempfile.mktemp(dir=temp_directory, prefix="GS_GST_resize_", suffix=".tiff")
        GST_ds = gdal.Open(GST_file_path)
        resize_tif(pan_ds, GST_ds, GST_resize_file)
        GST_ds = None
        # 计算全色和重采样后多光谱的最小重叠矩形
        coordinate = min_rect(pan_ds, GST_resize_file)
        # 将高分辨率全色影像和模拟全色影像进行匹配，使之和模拟全色影像具有相同的统计指数
        modified_pan_arr, zero_index = modify_pan_stat(pan_ds, simulated_pan_ds, coordinate)
        gc.collect()
        Inv_Gram_Schmidt_Transform(modified_pan_arr, GST_resize_file, transform_cofficient, coordinate, zero_index,
                                   fusion)
        # 删除临时文件
        shutil.rmtree(temp_directory)
        pan_ds = None

        gc.collect()
    shutil.rmtree(temp_dir)
    return None


if __name__ == '__main__':
    start_time = time.time()
    in_dir = r"F:\test_data\new_test\newtest"
    out_dir = r"F:\test_data\new_test\newtest\tmp"
    partfileinfo = "*MSS*.tif"
    # in_dir = sys.argv[1]
    # out_dir = sys.argv[2]
    # partfileinfo = None
    main(in_dir=in_dir, out_dir=out_dir, partfileinfo=partfileinfo)
    end_time = time.time()


    print("time: %.4f secs." % (end_time - start_time))
