#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2022/05/05 17:11
# @Author  : zhaoss
# @FileName: two_pass.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:

Parameters

"""
import os
import time
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def stats_hist(img_data, bg_val=0, no_bg=True):
    '''
    统计影像直方图，默认背景值为0，no_bg参数设置最终直方图中考虑不考虑背景值，默认不考虑
    '''
    # 获取影像的最大、最小值
    img_max = img_data.max()
    img_min = img_data.min()
    # 获取图像中灰度级范围的统计直方图
    bins = np.arange(start=img_min, stop=img_max + 2, step=1)
    n, xbin = np.histogram(img_data, bins=bins)
    n = n / np.sum(n)
    xbin = xbin[:-1]
    if no_bg:
        xbin_indx = np.where(xbin != bg_val)
        n = n[xbin_indx]
        n = n / np.sum(n)
        xbin = xbin[xbin_indx]
    return n[:], xbin[:]


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
    extended_val = np.pad(matrix, ((ys_fill, ys_fill), (xs_fill, xs_fill)),
                          'constant', constant_values=default_value)
    # extended_val = np.pad(matrix, ((ys_fill, ys_fill), (xs_fill, xs_fill)), 'reflect')
    matrix = None
    return extended_val


def gray_filtering(xs, ys, ori_xsize, ori_ysize, ext_img):
    """

    :param xs: 卷积核大小：列
    :param ys: 卷积核大小：行
    :param kernel: 卷积核
    :param ext_img: 经扩展后的影像
    :return: 滤波后的影像
    """
    # 使用切片后影像的波段数
    # 创建切片后存储矩阵
    channel = xs * ys
    filtered_img = np.zeros((channel, ori_ysize, ori_xsize), dtype=np.uint8)
    ichannel = 0
    for irow in range(ys):
        for icol in range(xs):
            filtered_img[ichannel, :, :] = ext_img[irow: irow +
                                                   ori_ysize, icol: icol + ori_xsize]
            ichannel += 1
    return filtered_img[:, :, :]


def gray_erode(win_size, src_data):
    ysize, xsize = src_data.shape
    extend_src_data = Extend(win_size, win_size, src_data, default_value=255)
    filter_img = gray_filtering(int(win_size), int(
        win_size), xsize, ysize, extend_src_data)
    dst_img = np.min(filter_img, axis=0)
    filter_img = None
    return dst_img


def gray_dilate(win_size, src_data):
    ysize, xsize = src_data.shape
    extend_src_data = Extend(win_size, win_size, src_data, default_value=0)
    filter_img = gray_filtering(int(win_size), int(
        win_size), xsize, ysize, extend_src_data)
    dst_img = np.max(filter_img, axis=0)
    filter_img = None
    return dst_img


def opening(win_size, thr, src_data):
    """
    先腐蚀后膨胀，光滑目标轮廓，消除小目标（如去掉毛刺和孤立点），在纤细出分离物体，常用于去除小颗粒噪声以及断开目标之间的粘连
    :param win_size:
    :param src_data:
    :return:
    """
    for _ in range(thr):
        src_data = gray_erode(win_size, src_data)
    for _ in range(thr):
        src_data = gray_dilate(win_size, src_data)
    return src_data


def closing(win_size, thr, src_data):
    """
    先膨胀后腐蚀，能够填平小湖（即小孔），弥合小裂缝，而总的位置和形状不变
    :param win_size:
    :param src_data:
    :return:
    """
    for _ in range(thr):
        src_data = gray_dilate(win_size, src_data)
    for _ in range(thr):
        src_data = gray_erode(win_size, src_data)
    return src_data


def spike_transf(size, op, src_data):
    '''对影像进行穗帽变换，即白顶帽变换和黑底帽变换
    :size: 进行开闭运算时选择的窗口大小
    :op: 选择进行何种变换,top_hat=0, bottom_hat=1
    '''
    src_data = np.pad(src_data, ((1, 1), (1, 1)),
                      'constant', constant_values=30)
    xsize = src_data.shape[1]
    ysize = src_data.shape[0]
    # 进行变换
    if op:
        filter_img = closing(size, 1, src_data)
        transf_img = filter_img - src_data
    else:
        filter_img = opening(size, 1, src_data)
        transf_img = src_data - filter_img
    # 对穗帽变换后的影像进行开运算，去除零星噪声点
    transf_img = opening(3, 3, transf_img)
    return transf_img[1:ysize - 1, 1:xsize - 1]


def ostu1D(image):
    # 获取影像直方图
    freq, bin = stats_hist(image, no_bg=False)
    # 计算累计直方图频率
    cdf = np.cumsum(freq)
    # 计算灰度值与其对应频率的累积值
    gray_freq = bin * freq
    udf = np.cumsum(gray_freq)
    # 获取二值化阈值
    class_var = 0
    threshold = 0
    for k in range(len(bin)):
        w0 = cdf[k]
        w1 = 1 - w0
        u0 = udf[k] / w0
        u1 = (udf[-1] - udf[k]) / w1
        tmp = w0 * w1 * (u0 - u1) * (u0 - u1)
        if tmp > class_var:
            class_var = tmp
            threshold = bin[k]
    # 影像二值化
    print("阈值为: {}".format(threshold))
    binary_img = np.where(image > threshold, 1, 0)
    return binary_img


def main(src, dst, op, size):
    # 定义连通域
    conn_4 = [[-1, 0, 0, 0, 1], [0, -1, 0, 1, 0]]
    conn_8 = [[-1, -1, -1, 0, 0, 0, 1, 1, 1], [-1, 0, 1, -1, 0, 1, -1, 0, 1]]
    # 打开影像
    dataset = gdal.Open(src)
    img_data = dataset.ReadAsArray()
    # 对影像进行白顶帽变换，抑制暗色背景
    top_hat_img = spike_transf(size, op, img_data)
    # 影像二值化
    img = ostu1D(top_hat_img)
    # 为了方便进行邻域判断将原始影响向外扩展一圈
    img_pad = np.pad(img, ((1, 1), (1, 1)), "constant", constant_values=0)
    rows, cols = img_pad.shape
    # 按照四邻域方式进行连通域检索
    label = 1
    # 确定使用的是那种邻域方式
    sign = len(conn_4[0]) // 2
    # 创建关系字典,用以记录像素属于哪个连通域
    label_dict = {}
    # 第一遍扫描
    for row in range(1, rows-1):
        for col in range(1, cols-1):
            # 逐个点位判断
            if img_pad[row, col] != 1:
                continue
            # 获取邻域像素值
            pixel_coor = ([i + row for i in conn_4[0]],
                          [j + col for j in conn_4[1]])
            conn_vals = img_pad[pixel_coor]
            valid_vals = conn_vals[0: sign]
            if sum(valid_vals) == 0:
                # 全为无效值
                img_pad[row, col] = label
                label_dict[label] = label
                label += 1
            else:
                # 部分或全部为有效值
                min_valid_val = min(valid_vals[np.nonzero(valid_vals)])
                img_pad[row, col] = min_valid_val
                for val in valid_vals[np.nonzero(valid_vals)]:
                    # 新建立的关系比原来的关系大则不改变
                    if label_dict[min_valid_val] < label_dict[val]:
                        label_dict[val] = label_dict[min_valid_val]
    # 第二遍扫描，完成连通域的填充，并统计每个连通域像素个数
    # 创建每个连通域像素个数统计字典
    conn_num_dict = dict.fromkeys(set(label_dict.values()), 0)
    for row in range(1, rows-1):
        for col in range(1, cols-1):
            # 逐个点位判断
            if img_pad[row, col] == 0:
                continue
            flag = label_dict[img_pad[row, col]]
            img_pad[row, col] = flag
            conn_num_dict[flag] += 1
    # 回复原图像，并输出统计结果
    res_img = img_pad[1: rows - 1, 1: cols - 1]
    # 创建输出影像
    drv = gdal.GetDriverByName('GTiff')
    dst_ds = drv.Create(dst, cols - 2, rows - 2, 1, gdal.GDT_UInt16)
    dstband = dst_ds.GetRasterBand(1)
    dstband.WriteArray(res_img)
    dstband.FlushCache()
    # 统计结果
    print("共有{}个连通域".format(len(conn_num_dict)))
    print("+++++++++++++++++++++++++++++++++++++++++++++")
    for k, v in conn_num_dict.items():
        print("第{}个连通域的像素值个数为：{}".format(k, v))
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
    src_path = r"F:\test_data\DIP3E_out\Fig0940(a).tif"
    dst_path = r"F:\test_data\DIP3E_out\Fig0940(a)_res2.tif"
    # 选择进行的形态学运算top_hat=0, bottom=1
    operate = 0
    # 结构元大小（即窗口大小-SE size)
    se_size = 31
    main(src_path, dst_path, operate, se_size)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
