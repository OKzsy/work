#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2022/05/06 14:20
# @Author  : zhaoss
# @FileName: seed_filling.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:

Parameters

"""
from itertools import count
import os
import time
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def seed_mark(conn, label, irow, icol):
    # 引用全局影像变量
    global img_pad
    global count
    # 标记种子点
    img_pad[irow, icol] = label
    count += 1
    # 获取邻域像素值
    pixel_coor = ([i + irow for i in conn[0]], [j + icol for j in conn[1]])
    conn_num = len(pixel_coor[0])
    for ival in range(conn_num):
        conn_row = pixel_coor[0][ival]
        conn_col = pixel_coor[1][ival]
        if img_pad[conn_row, conn_col] != 1:
            continue
        seed_mark(conn, label, conn_row, conn_col)
    return None


def main():
    # 定义连通域
    conn_4 = [[-1, 0, 0, 1], [0, -1, 1, 0]]
    conn_8 = [[-1, -1, -1, 0, 0, 1, 1, 1], [-1, 0, 1, -1, 1, -1, 0, 1]]
    # 模拟二值图像
    img_list = [[0, 0, 1, 0, 0, 1, 0],
                [1, 1, 1, 0, 1, 1, 1],
                [0, 0, 1, 0, 0, 1, 0],
                [0, 1, 1, 0, 1, 1, 0]
                ]
    img = np.array(img_list)
    # 为了方便进行邻域判断将原始影响向外扩展一圈
    global img_pad
    img_pad = np.pad(img, ((1, 1), (1, 1)), "constant", constant_values=0)
    rows, cols = img_pad.shape
    # 设置初始标识
    label = 2
    # 创建每个连通域像素个数统计字典
    conn_count = {}
    # 逐像素循环判断
    for row in range(1, rows - 1):
        for col in range(1, cols - 1):
            # 统计每个连通域的个数
            global count
            count = 0
            # 逐个点位判断
            if img_pad[row, col] != 1:
                continue
            seed_mark(conn_8, label, row, col)
            conn_count[label] = count
            label += 1
    # 恢复原图像，并输出统计结果
    res_img = img_pad[1: rows - 1, 1: cols - 1]
    img_pad = None
    # 统计结果
    print("共有{}个连通域".format(len(conn_count)))
    print("+++++++++++++++++++++++++++++++++++++++++++++")
    for k, v in conn_count.items():
        print("第{}个连通域的像素值个数为：{}".format(k - 1, v))
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
    main()
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
