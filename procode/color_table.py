#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import glob
import numpy as np
import time
from osgeo import gdal


def color(infile, outfile, deep_leaning_table, all_sample_labels):
    # 注册所有gdal的驱动
    gdal.AllRegister()
    gdal.SetConfigOption("gdal_FILENAME_IS_UTF8", "YES")

    # 打开源影像
    source_ds = gdal.Open(infile)
    prj = source_ds.GetProjection()
    geo = source_ds.GetGeoTransform()
    in_band = source_ds.GetRasterBand(1)
    a_nodata = in_band.GetNoDataValue()
    # 创建输出影像
    gtiff_driver = gdal.GetDriverByName('GTiff')
    dest_ds = gtiff_driver.Create(outfile, in_band.XSize, in_band.YSize, 1, gdal.GDT_Byte)
    dest_ds.SetProjection(prj)
    dest_ds.SetGeoTransform(geo)

    out_band1 = dest_ds.GetRasterBand(1)
    if not a_nodata == None:
        out_band1.SetNoDataValue(a_nodata)
    # 临时处理影像
    in_array = in_band.ReadAsArray()
    in_array = np.where(in_array == 0, 30, 0)
    out_band1.WriteArray(in_array)
    # 写入颜色表
    colors = gdal.ColorTable()
    for key, value in deep_leaning_table.items():
        colors.SetColorEntry(key, all_sample_labels[value][1])

    out_band1.SetRasterColorTable(colors)

    source_ds = None
    dest_ds = None


def main(infile, outfile, deep_leaning_table):
    all_sample_labels = {'白菜': [1, (0, 153, 102)], '包菜': [2, (153, 204, 51)], '菠菜': [3, (0, 102, 51)],
                         '草莓': [4, (255, 153, 204)], '大葱': [5, (204, 204, 102)], '大蒜': [6, (34, 139, 34)],
                         '冬瓜': [7, (153, 204, 153)], '豆角': [8, (51, 102, 102)], '番茄': [9, (51, 51, 153)],
                         '红薯': [10, (153, 0, 51)], '花菜': [11, (102, 102, 153)], '花生': [12, (255, 153, 0)],
                         '黄瓜': [13, (93, 154, 66)], '芥兰': [14, (0, 51, 102)], '苦瓜': [15, (61, 61, 140)],
                         '苦菊': [16, (105, 107, 182)], '辣椒': [17, (255, 102, 102)], '萝卜': [18, (50, 40, 239)],
                         '棉花': [19, (0, 102, 153)], '南瓜': [20, (102, 51, 0)], '茄子': [21, (102, 51, 102)],
                         '芹菜': [22, (153, 102, 102)], '青菜': [23, (38, 254, 2)], '生菜': [24, (38, 54, 209)],
                         '甜瓜': [25, (26, 131, 191)], '莴笋': [26, (137, 249, 147)], '西瓜': [27, (28, 80, 33)],
                         '西兰花': [28, (141, 169, 143)], '苋菜': [29, (53, 109, 59)], '小麦': [30, (255, 255, 0)],
                         '烟草': [31, (255, 0, 0)], '烟草+地膜': [32, (248, 90, 53)], '烟草+麦茬': [33, (215, 73, 40)],
                         '烟草+麦茬西瓜': [34, (148, 49, 26)], '烟草+红薯': [35, (236, 62, 123)], '洋葱': [36, (98, 49, 200)],
                         '油麦菜': [37, (6, 97, 149)], '玉米': [38, (210, 210, 5)], '杂草': [39, (124, 124, 35)],
                         '葡萄': [40, (140, 0, 255)], '林地': [41, (140, 0, 255)], '其它': [254, (255, 255, 255)],
                         '背景': [0, (255, 255, 255)]}
    color(infile, outfile, deep_leaning_table, all_sample_labels)


if __name__ == '__main__':
    start_time = time.clock()
    infile = r"\\192.168.0.234\nydsj\user\DYR\郑州菜篮子\gongyi_20190108_xiaomai\result_zong\tif\temp\res\gongyi_guge_xiaomai_clip.tif"
    outfile = r"\\192.168.0.234\nydsj\user\DYR\郑州菜篮子\gongyi_20190108_xiaomai\result_zong\tif\temp\res\gongyi_guge_xiaomai_color.tif"
    if os.path.exists(outfile):
        os.remove(outfile)
    deep_leaning_table = {30: '小麦', 0: '背景'}
    main(infile, outfile, deep_leaning_table)
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
