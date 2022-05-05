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
from asyncio import constants
import os
import time
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def main():
    # 定义连通域
    conn_4 = [[-1, 0, 0, 0, 1], [0, -1, 0, 1, 0]]
    conn_8 = [[-1, -1, -1, 0, 0, 0, 1, 1, 1],[-1, 0, 1, -1, 0, 1, -1, 0, 1]]
    # 模拟二值图像
    img_list = [[0, 0, 1, 0, 0, 1, 0],
           [1, 1, 1, 0, 1, 1, 1],
           [0, 0, 1, 0, 0, 1, 0],
           [0, 1, 1, 0, 1, 1, 0]
    ]
    img = np.array(img_list)
    # 为了方便进行邻域判断将原始影响向外扩展一圈
    img_pad = np.pad(img, ((1, 1), (1, 1)), "constant", constant_values=0)
    rows, cols = img_pad.shape
    # 按照四邻域方式进行连通域检索
    label = 1
    # 确定使用的是那种邻域方式
    sign = len(conn_4[0]) // 2
    for row in range(1, rows-1):
        for col in range(1, cols-1):
            # 逐个点位判断
            if img_pad[row, col] != 1:
                continue
            # 获取邻域像素值
            pixel_coor = [[i + row for i in conn_4[0]], [j + col for j in conn_4[1]]]
            conn_val = img_pad[pixel_coor]
            valid_val = conn_val[0: sign]
            sum_conn_val = sum(valid_val)
            if sum_conn_val == 0:
                img_pad[row, col] = label
                label += 1
            elif sum_conn_val >= sign:
                img_pad[row, col] = min(valid_val)
            else:
                

            min_conn_val = min(conn_val)
            if min_conn_val > 1:
                pass
            else:
                img_pad[row, col] = label
                label += 1
                pass

            pass
        pass


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