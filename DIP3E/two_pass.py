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
           [1, 1, 1, 1, 1, 1, 1],
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
    # 创建关系字典,用以记录像素属于哪个连通域
    label_dict = {}
    # 第一遍扫描
    for row in range(1, rows-1):
        for col in range(1, cols-1):
            # 逐个点位判断
            if img_pad[row, col] != 1:
                continue
            # 获取邻域像素值
            pixel_coor = ([i + row for i in conn_4[0]], [j + col for j in conn_4[1]])
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
                    label_dict[val] = min_valid_val
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
    main()
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))