#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2020/11/4 11:40
# @Author  : zhaoss
# @FileName: glcm.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
用于生成灰度共生矩阵, 该算法可以使用影像的切片加上BIP存储方式进行按行读取加速。arr.reshape(bands,xsize * ysize).T

Parameters


"""

import os
import sys
import glob
import time
import math
import fnmatch
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def glmc(matrix, win_size, angle):
    """

    :param matrix: 原始矩阵
    :param angle: 方向角度值
    :return:
    """
    # 根据角度确定dx(列偏移量), dy(行偏移量)的值和对应的归一化常数
    ori_raw, ori_col = win_size
    direction = {0: (1, 0),
                 45: (1, 1),
                 90: (0, 1),
                 135: (-1, 1)}
    dx, dy = direction[angle]
    # 根据相邻关系计算新的矩阵大小
    matrix = matrix.reshape(win_size)
    new_raw = ori_raw + abs(dy)
    new_col = ori_col + abs(dx)
    new_mat = np.zeros((new_raw, new_col), dtype=np.int16) - 999
    point_y = 0 if dy >= 0 else abs(dy)
    point_x = 0 if dx >= 0 else abs(dx)
    new_mat[point_y: point_y + ori_raw, point_x: point_x + ori_col] = matrix
    # 生成灰度矩阵
    unique_val = list(np.unique(matrix))
    if -999 in unique_val:
        unique_val.remove(-999)
    unique_val_num = len(unique_val)
    hc = np.zeros((unique_val_num, unique_val_num), dtype=np.uint16)
    for i in range(unique_val_num):
        ivalue = unique_val[i]
        index_raw, index_col = np.where(new_mat == ivalue)
        index_raw += dy
        index_col += dx
        tmp_mat = new_mat[(index_raw, index_col)]
        tmp_unique = np.unique(tmp_mat, return_counts=True)
        tmp_unique_num = len(tmp_unique[0])
        if tmp_unique_num == 1 and tmp_unique[0][0] == -999:
            continue
        else:
            tmp_res = np.zeros(unique_val_num, dtype=np.int16)
            for j in range(tmp_unique_num):
                tmp = tmp_unique[0][j]
                if not tmp == -999:
                    val_index = unique_val.index(tmp)
                    tmp_res[val_index] = tmp_unique[1][j]
            hc[i, :] = tmp_res
    # 对灰度共生矩阵进行归一化
    normaliz_hc = hc * (1 / np.sum(hc))
    unique_arr = np.array(unique_val)
    # 计算灰度共生矩阵的二阶矩
    hc_asm = np.sum(normaliz_hc * normaliz_hc)
    hc_asm = int(hc_asm * 100000)
    # # 计算灰度共生矩阵的均值(包括行均值mr和列均值mc)
    unique_arr_mat = unique_arr.reshape(-1, 1) + np.zeros(unique_val_num)
    hc_mean_r = np.sum(np.sum(unique_arr_mat * normaliz_hc, axis=1))
    hc_mean_c = np.sum(np.sum(unique_arr_mat * normaliz_hc.T, axis=1))
    # 计算灰度共生矩阵的方差
    unique_square_r = (unique_arr_mat - hc_mean_r) * (unique_arr_mat - hc_mean_r)
    unique_square_c = (unique_arr_mat - hc_mean_c) * (unique_arr_mat - hc_mean_c)
    hc_var_r = np.sqrt(np.sum(np.sum(unique_square_r * normaliz_hc, axis=1)))
    hc_var_c = np.sqrt(np.sum(np.sum(unique_square_c * normaliz_hc.T, axis=1)))
    # 计算灰度共生矩阵的对比度
    tmp_con = unique_arr_mat - unique_arr_mat.T
    hc_con = np.sum(tmp_con * tmp_con * normaliz_hc)
    hc_con = int(hc_con)
    # 计算灰度共生矩阵的相关性
    tmp_cor = (unique_arr_mat - hc_mean_r) * (unique_arr_mat.T - hc_mean_c) * (1 / (hc_var_r * hc_var_c + 0.000001))
    hc_cor = np.sum(tmp_cor * normaliz_hc)
    hc_cor = int(hc_cor * 10000)
    # 计算灰度共生矩阵的熵
    hc_ent = -np.sum(normaliz_hc * np.log2(normaliz_hc, where=normaliz_hc > 0))
    if math.isnan(hc_ent):
        hc_ent = 0
    hc_ent = int(hc_ent * 100)
    hc_mean = int((hc_mean_r + hc_mean_c) * 0.5)
    hc_var = int((hc_var_r + hc_var_c) * 0.5)
    return np.array([hc_mean, hc_var, hc_asm, hc_con, hc_cor, hc_ent])

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


def filtering(xs, ys, ori_xsize, ori_ysize, ext_img):
    """

    :param xs: 卷积核大小：列
    :param ys: 卷积核大小：行
    :param kernel: 卷积核
    :param ext_img: 经扩展后的影像
    :return: 滤波后的影像
    """
    # 使用切片后影像的波段书
    # 创建切片后存储矩阵
    channel = xs * ys
    filtered_img = np.zeros((channel, ori_ysize, ori_xsize), dtype=np.int16)
    ichannel = 0
    for irow in range(ys):
        for icol in range(xs):
            filtered_img[ichannel, :, :] = ext_img[irow: irow + ori_ysize, icol: icol + ori_xsize]
            ichannel += 1
    filtered_img = filtered_img.reshape(channel, ori_xsize * ori_ysize).T
    return filtered_img


def main(src, dst):
    # 定义窗口大小
    win = (7, 7)
    # 打开影像
    src_ds = gdal.Open(src)
    xsize = src_ds.RasterXSize
    ysize = src_ds.RasterYSize
    src_prj = src_ds.GetProjection()
    src_geo = src_ds.GetGeoTransform()
    # 获取指定波段用于计算纹理
    src_arr = src_ds.GetRasterBand(1).ReadAsArray()
    src_arr = src_arr.astype(np.int16)
    # 整理数据，便于获取窗口数据
    extend_img = Extend(win[0], win[1], src_arr, -999)
    filted_img = filtering(win[0], win[1], xsize, ysize, extend_img)
    # 计算纹理
    # 创建存放纹理结果的矩阵
    texture_mat = np.zeros((xsize * ysize, 6), dtype=np.int16)
    mid_idx = int(win[0] * win[1] / 2)
    for iraw in range(xsize * ysize):
        if filted_img[iraw, mid_idx] == 0:
            texture_mat[iraw, :] = 0
        else:
            itex = glmc(filted_img[iraw, :], win, 0)
            texture_mat[iraw, :] = itex
    texture_res = texture_mat.T.reshape(6, ysize, xsize)
    # 输出纹理信息
    drv = gdal.GetDriverByName('GTiff')
    dst_ds = drv.Create(dst, xsize, ysize, 6, gdal.GDT_Int16)
    dst_ds.SetGeoTransform(src_geo)
    dst_ds.SetProjection(src_prj)
    for iband in range(6):
        dst_ds.GetRasterBand(iband + 1).WriteArray(texture_res[iband, :, :])
    dst_ds.FlushCache()
    src_ds = dst_ds = None


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
    src_file = r"\\192.168.0.234\nydsj\user\ZSS\郏县林地test\2.data\2.S2\3.clip\L2A_T49SFT_T49SGT_20200601T031149_test.tif"
    dst_file = r"\\192.168.0.234\nydsj\user\ZSS\郏县林地test\2.data\2.S2\3.clip\L2A_T49SFT_T49SGT_20200601T031149_tex.tif"
    main(src_file, dst_file)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
