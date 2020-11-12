#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2020/11/11 11:50
# @Author  : zhaoss
# @FileName: multi_texture.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import sys
import glob
import time
import fnmatch
import numpy as np
import numba as nb
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress

import os
import sys
import glob
import time
import math
import fnmatch
import numpy as np
import multiprocessing as mp
from osgeo import gdal, ogr, osr, gdalconst

from datablock import DataBlock

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


class Bar():
    """用于多线程显示进度条"""
    members = 0

    def __init__(self, total):
        self.total = total

    def update(self):
        Bar.members += 1
        progress(Bar.members / self.total)

    def shutdown(self):
        Bar.members = 0


@nb.njit()
def cyunique(a):
    n = a.shape[0]
    label_num = 0
    max_i = a[0]
    min_i = a[0]
    for i in range(n):
        max_i = max(max_i, a[i])
        min_i = min(min_i, a[i])
    min_i = min(min_i, 0)
    max_i -= min_i
    real_total = max_i + 1
    unique = np.zeros(real_total, dtype=np.int16)
    label = np.zeros(real_total, dtype=np.int16)
    label_count = np.zeros(real_total, dtype=np.uint32)
    for i in range(n):
        tmp = a[i] - min_i
        label_count[tmp] += 1
        if not unique[tmp]:
            label_num += 1
            unique[tmp] = 1
            label[tmp] = tmp
    start = 0
    if min_i == -999:
        label_num -= 1
        start = 1
    res_label = np.zeros(label_num, dtype=np.int16)
    res_label_count = np.zeros(label_num, dtype=np.uint32)
    ires = 0
    for i in range(start, real_total):
        if unique[i]:
            res_label[ires] = label[i] + min_i
            res_label_count[ires] = label_count[i]
            ires += 1
    return (res_label, res_label_count, label_num)


@nb.njit()
def glmc_cor(new_mat_ravel, new_col, dy, dx):
    """

    :param matrix:
    :param dy: 行偏移
    :param dx: 列偏移
    :return:
    """
    # 生成灰度矩阵
    unique = cyunique(new_mat_ravel)
    unique_val = unique[0]
    unique_val_num = unique[2]
    hc = np.zeros((unique_val_num, unique_val_num), dtype=np.uint16)
    for ihc in range(unique_val_num):
        ivalue = unique_val[ihc]
        index = np.where(new_mat_ravel == ivalue)
        new_index = index[0] + (new_col * dy + dx)
        tmp_mat = new_mat_ravel[new_index]
        tmp_unique = cyunique(tmp_mat)
        tmp_unique_num = tmp_unique[2]
        tmp_res = np.zeros(unique_val_num, dtype=np.int16)
        for i in range(tmp_unique_num):
            tmp = tmp_unique[0][i]
            for j in range(unique_val_num):
                if tmp == unique_val[j]:
                    tmp_res[j] = tmp_unique[1][i]
                    break
        hc[ihc, :] = tmp_res
    return hc


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
    new_mat_ravel = new_mat.ravel()
    matrix = new_mat = None
    unique = cyunique(new_mat_ravel)
    unique_val = unique[0]
    unique_val_num = unique[2]
    # 生成灰度共生矩阵
    hc = glmc_cor(new_mat_ravel, new_col, dy, dx)
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


def init_pool(in_shared, out_share, in_shape, out_shape, in_dt, out_dt):
    """
    多线程准备函数
    :param in_shared: 原始数据
    :param out_share: 输出数据
    :param in_shape: 原始数据形状
    :param out_shape: 输出数据形状
    :param in_dt: 原始数据类型
    :param out_dt: 输出数据类型
    :return:
    """
    global global_in_share
    global global_out_share
    global IN_SHAPE
    global OUT_SHAPE
    global in_dtype
    global out_dtype
    global_in_share = in_shared
    global_out_share = out_share
    IN_SHAPE = in_shape
    OUT_SHAPE = out_shape
    in_dtype = in_dt
    out_dtype = out_dt


def cal_glmc(win, img_block, IDblock):
    # 从共享内存中提取数据
    share_in_data = np.frombuffer(global_in_share, in_dtype).reshape(IN_SHAPE)
    share_out_data = np.frombuffer(global_out_share, out_dtype).reshape(
        OUT_SHAPE)
    dims_get, dims_put = img_block.block(IDblock)
    in_data = share_in_data[dims_get[1]: dims_get[1] + dims_get[3],
              dims_get[0]: dims_get[0] + dims_get[2]]
    out_data = share_out_data[dims_get[1]: dims_get[1] + dims_get[3],
               dims_get[0]: dims_get[0] + dims_get[2]]
    # 计算纹理
    mid_idx = int(win[0] * win[1] / 2)
    ysize = in_data.shape[1]
    xsize = in_data.shape[0]
    for iraw in range(xsize * ysize):
        if in_data[iraw, mid_idx] == 0:
            out_data[iraw, :] = 0
        else:
            itex = glmc(in_data[iraw, :], win, 0)
            out_data[iraw, :] = itex
    # 将分类的数据放回共享内存中
    share_out_data[dims_put[3]:dims_put[3] + dims_put[1],
    dims_put[2]: dims_put[2] + dims_get[2]] = out_data
    in_data = out_data = None
    return 1


def main(src, dst):
    imgtype2ctype = {'uint8': 'B', 'uint16': 'H', 'int16': 'h',
                     'uint32': 'I', 'int32': 'i',
                     'float32': 'f', 'float64': 'd'}
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
    # 为待计算纹理数据创建共享内存
    typecode = filted_img.dtype.name
    in_dt = np.dtype(typecode)
    in_shape = filted_img.shape
    pixel_len = int(np.prod(np.array(in_shape)))
    ori_share = mp.RawArray(imgtype2ctype[typecode], pixel_len)
    ori_share_arr = np.frombuffer(ori_share, in_dt).reshape(in_shape)
    ori_share_arr[:, :] = filted_img
    # 为结果创建共享内存
    # 创建存放纹理结果的矩阵
    texture_mat = np.zeros((xsize * ysize, 6), dtype=np.int16)
    typecode = texture_mat.dtype.name
    out_dt = np.dtype(typecode)
    out_shape = texture_mat.shape
    pixel_len = int(np.prod(np.array(out_shape)))
    out_share = mp.RawArray(imgtype2ctype[typecode], pixel_len)
    out_share_arr = np.frombuffer(out_share, out_dt).reshape(out_shape)
    out_share_arr[:, :] = texture_mat
    texture_mat = None
    # 分块并行处理
    # 引用DataBlock类
    share_xsize = in_shape[1]
    share_ysize = in_shape[0]
    img_block = DataBlock(share_xsize, share_ysize, 1000, 0)
    numsblocks = img_block.numsblocks
    # 进行多线程分类
    # 确定进程数量
    cpu_count = os.cpu_count() - 1
    tasks = cpu_count if cpu_count <= numsblocks else numsblocks
    # 创建线程池
    pool = mp.Pool(processes=tasks, initializer=init_pool,
                   initargs=(ori_share, out_share, in_shape, out_shape, in_dt, out_dt))
    # 定义进度条
    bar = Bar(numsblocks)
    update = lambda args: bar.update()
    # 进行纹理计算
    for itask in range(numsblocks):
        pool.apply_async(cal_glmc,
                         args=(win, img_block, itask), callback=update)
    pool.close()
    pool.join()
    bar.shutdown()
    # itask = 0
    # cal_glmc(ori_share, out_share, in_shape, out_shape, in_dt, out_dt, win, img_block, itask)
    # 写出结果
    # 从共享内存获取结果
    out_arr = np.frombuffer(out_share, out_dt).reshape(out_shape)
    texture_res = out_arr.T.reshape(6, ysize, xsize)
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
    src_file = r"\\192.168.0.234\nydsj\user\ZSS\郏县林地test\2.data\2.S2\3.clip\L2A_T49SFT_T49SGT_20200706_jiaxian.tif"
    dst_file = r"\\192.168.0.234\nydsj\user\ZSS\郏县林地test\2.data\2.S2\3.clip\L2A_T49SFT_T49SGT_20200601T031149_tex_multi.tif"
    main(src_file, dst_file)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
