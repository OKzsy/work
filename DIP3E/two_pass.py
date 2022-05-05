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
    for row in (1, rows-1):
        for col in (1, cols-1):
            # 判断种子点即连通域开始点位
            if img_pad[row - 1, col] + img_pad[row, col - 1] != 0:
                continue
            

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