# !/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/12/3 10:58
# @Author  : zhaoss
# @FileName: gaussian_pyr.py
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
import fnmatch
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst

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
    # 根据目标大小，在内存创建结果影像
    tmp_dst_path = r'/vsimem/tmp_dst_{}.tiff'.format(str(seq))
    gdal.Translate(tmp_dst_path, src_dst, resampleAlg=gdalconst.GRA_Bilinear, format='GTiff', width=dst_xsize,
                   height=dst_ysize, outputType=gdalconst.GDT_Float32)
    tmp_dst = gdal.Open(tmp_dst_path)
    src_dst = None
    gdal.Unlink(tmp_dst_path)
    gc.collect()
    return tmp_dst


def Extend(xs, ys, matrix):
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
    extended_val = np.pad(matrix, ((ys_fill, ys_fill), (xs_fill, xs_fill)), "reflect")
    matrix = None
    return extended_val


def gaussian_template_one(sigma_val):
    # opencv认为当图像为8bit时，其能量集中再3个方差内，否则为4个方差内，有待考究
    # ksize = round(2 * round(3 * sigma_val) + 1)
    ksize = round(2 * round(4 * sigma_val) + 1)
    template = np.zeros(ksize, dtype=np.float32)
    for element in range(ksize):
        u = element - ksize // 2
        template[element] = math.exp(-u ** 2 / (2 * sigma_val ** 2))
    return ksize, template / np.sum(template)


def img_filtering(xs, ys, ori_xsize, ori_ysize, kernel, ext_img):
    """

    :param xs: 卷积核大小：列
    :param ys: 卷积核大小：行
    :param kernel: 卷积核
    :param ext_img: 经扩展后的影像
    :return: 滤波后的影像
    """
    # 使用切片后影像的波段书
    # 创建切片后存储矩阵
    filtered_img_h = np.zeros((ori_ysize + ys - 1, ori_xsize), dtype=np.float32)
    for icol in range(xs):
        filtered_img_h += ext_img[:, icol: icol + ori_xsize] * kernel[icol]
    ext_img = None
    filtered_img = np.zeros((ori_ysize, ori_xsize), dtype=np.float32)
    for irow in range(ys):
        filtered_img += filtered_img_h[irow: irow + ori_ysize, :] * kernel[irow]
    filtered_img_h = None
    return filtered_img


def scale_space(sigma):
    """
    计算高斯尺度金子塔的相对模糊尺度
    :param sigma: 自定义高斯金字塔初始尺度
    :param camera_sigma: 影像采集时镜头的模糊尺度
    :return: 尺度金字塔的相对模糊模糊尺度
    """
    # 定义高斯尺度空间中每组各层的尺度间隔
    k = 2 ** (1 / 3)
    # 计算该层的尺度空间参数
    scales_para = []
    scales_para.append(sigma)
    for iscal_spatial in range(1, 6):
        sig_prev = k ** (iscal_spatial - 1) * sigma
        sig_total = sig_prev * k
        scales_para.append(math.sqrt(sig_total ** 2 - sig_prev ** 2))
    return scales_para[:]


def detect_ext_points(gauss_diff_pyr):
    """
    对输入的高斯差分金字塔进行极值点检测
    :param gauss_diff_pyr: 高斯差分金字塔
    :return: 极值点
    """
    return 1


def build_dog(src_array, scale_para):
    """
    根据空间尺度参数构建高斯差分金字塔，根据sift算法的原理，只计算2-5层
    :param src_array: 构建高斯差分金字塔的初始数据
    :param scale_para: 高斯空间尺度参数
    :return: 高斯差分金字塔和高斯金字塔下一层初始数据
    """
    xsize = src_array.shape[1]
    ysize = src_array.shape[0]
    # 创建存储高斯差分金字塔的数组
    gauss_matrix = np.zeros((6, ysize, xsize), dtype=np.float32)
    dog_matrix = np.zeros((5, ysize, xsize), dtype=np.float32)
    for ilayer in range(6):
        if ilayer == 0:
            dog_matrix[ilayer, :, :] = src_array
            gauss_matrix[ilayer, :, :] = src_array
            continue
        sigmaf = scale_para[ilayer]
        win_size, template = gaussian_template_one(sigmaf)
        kernel_xsize = kernel_ysize = win_size
        # 结合滤波函数对待滤波影像进行边缘扩展，目的是保证滤波结果和原始影像大小一致
        extended_img = Extend(kernel_xsize, kernel_ysize, src_array)
        # 使用模板进行滤波
        filtered_img = img_filtering(kernel_xsize, kernel_ysize, xsize, ysize, template, extended_img)
        extended_img = None
        src_array = filtered_img
        filtered_img = None
        gauss_matrix[ilayer, :, :] = src_array
        # 输出下高斯金字塔下一层的原始数据
        if ilayer == 3:
            mem_driver = gdal.GetDriverByName("MEM")
            next_dst = mem_driver.Create('', xsize, ysize, 1, gdal.GDT_Float32)
            next_dst.GetRasterBand(1).WriteArray(src_array)
        # 计算高斯差分金字塔并存储
        if ilayer == 5:
            dog_matrix[ilayer - 1, :, :] = src_array - dog_matrix[ilayer - 1, :, :]
        else:
            dog_matrix[ilayer, :, :] = src_array
            dog_matrix[ilayer - 1, :, :] = src_array - dog_matrix[ilayer - 1, :, :]
        gc.collect()
    return next_dst, dog_matrix, gauss_matrix


def pyramid(octave_val, src_dst, points, scale, n=0):
    if n == octave_val:  # 当达到指定层数后，返回监测的极值点
        # 返回极值点，可是设定在该返回位置做最后一层
        # 获取原始数据集的基本信息
        src_xsize = src_dst.RasterXSize
        src_ysize = src_dst.RasterYSize
        new_dst = resize(src_dst, int(src_xsize / 2), int(src_ysize / 2), n)  # 缩小一倍
        src_dst = None
        filtered_img = new_dst.ReadAsArray()
        # 建立高斯差分金字塔
        next_dst, dog_pyr, gauss_pyr = build_dog(filtered_img, scale)
        # 监测极值点，包括极值点定位
        # points.append(list(range(int(dataset))))
        return points
    else:
        if n == 0:
            # 获取原始数据集的基本信息
            src_xsize = src_dst.RasterXSize
            src_ysize = src_dst.RasterYSize
            new_dst = resize(src_dst, src_xsize * 2, src_ysize * 2, n)  # 放大一倍
            src_dst = None
            src_val = new_dst.ReadAsArray()
            # 针对第一组第一层需要考虑镜头模糊度进行特殊处理
            init_sigma_diff = math.sqrt(scale[0] ** 2 - (2 * init_camera_sigma) ** 2)
            win_size, template = gaussian_template_one(init_sigma_diff)
            kernel_xsize = kernel_ysize = win_size
            # 结合滤波函数对待滤波影像进行边缘扩展，目的是保证滤波结果和原始影像大小一致
            extended_img = Extend(kernel_xsize, kernel_ysize, src_val)
            # 使用模板进行滤波
            filtered_img = img_filtering(kernel_xsize, kernel_ysize, src_xsize * 2, src_ysize * 2, template,
                                         extended_img)
            extended_img = None
            # 建立高斯差分金字塔
            next_dst, dog_pyr, gauss_pyr = build_dog(filtered_img, scale)
            filtered_img = None
            # 检测极值点
            ext_points = detect_ext_points(dog_pyr)
            # 监测极值点，包括极值点定位
            # points.append(list(range(int(dataset))))
            return pyramid(octave_val, next_dst, points[:], scale, n + 1)
        else:
            # 获取原始数据集的基本信息
            src_xsize = src_dst.RasterXSize
            src_ysize = src_dst.RasterYSize
            new_dst = resize(src_dst, int(src_xsize / 2), int(src_ysize / 2), n)  # 缩小一倍
            src_dst = None
            filtered_img = new_dst.ReadAsArray()
            # 建立高斯差分金字塔
            next_dst, dog_pyr, gauss_pyr = build_dog(filtered_img, scale)
            # 监测极值点，包括极值点定位
            # points.append(list(range(int(dataset))))
            return pyramid(octave_val, next_dst, points[:], scale, n + 1)


def main(in_fn, band_index):
    init_sigma = 1.6
    global init_camera_sigma
    init_camera_sigma = 0.5
    # 读取影像
    src_dst = gdal.Open(in_fn)
    xsize = src_dst.RasterXSize
    ysize = src_dst.RasterYSize
    ori_band = src_dst.GetRasterBand(band_index)
    dtype = ori_band.DataType
    # 提取单波段为一个数据集进行高斯尺度金字塔构建
    driver = gdal.GetDriverByName('MEM')
    src_one_dst = driver.Create('', xsize, ysize, 1, dtype)
    src_one_dst.GetRasterBand(1).WriteArray(ori_band.ReadAsArray())
    src_dst = ori_band = None
    # 确定高斯金子塔的组数
    octave = math.floor(math.log(min(xsize, ysize), 2) / 2)
    if octave > 5:
        octave = 5
    # 计算该层的高斯尺度空间
    scale = scale_space(init_sigma)
    # 构建高斯金字塔并检测极值点
    extreme_points = []
    extreme_points = pyramid(octave, src_one_dst, extreme_points[:], scale)
    # num = 0
    # o = 4
    # dataset = 10
    # res_points = []
    # res = pyramid(num, o, dataset, res_points[:])
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
    in_file = r"F:\SIFT\left_one_band.PNG"
    # in_file = r"F:\test_data\new_test\GF2_20180718_L1A0003330812_sha.tiff"
    band_idx = 1
    main(in_file, band_idx)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
