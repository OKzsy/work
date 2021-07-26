#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2021/3/23 16:46
# @Author  : zhaoss
# @FileName: test_colormap.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
测试创建图例

Parameters


"""

import os
import time
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.colors import ListedColormap
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress
colormap = {
    0.00001: [255, 0, 0],
    0.25: [255, 210, 128],
    0.3: [255, 255, 0],
    0.45: [170, 255, 0],
    1.1: [85, 255, 0]
}


def color_bar(dst, labels, title):
    # 生成colorbar颜色
    color = np.ones((256, 4))
    breakpoints = [float(k) for k in list(colormap.keys())]
    min_breakpoint = min(breakpoints)
    max_breakpoint = max(breakpoints)
    src_array = np.linspace(min_breakpoint, max_breakpoint - 0.01 * max_breakpoint, 256)
    for ichanel in range(3):
        for ibreak in range(len(breakpoints) - 1):
            breakpoint1 = breakpoints[ibreak]
            breakpoint2 = breakpoints[ibreak + 1]
            color1 = colormap[breakpoint1][ichanel]
            color2 = colormap[breakpoint2][ichanel]
            # 创建拉伸方程
            temp_index = np.where((src_array >= breakpoint1) & (src_array < breakpoint2))
            color[temp_index[0], ichanel] = ((src_array[temp_index] - breakpoint1) * (color2 - color1) / (
                    breakpoint2 - breakpoint1) + color1).astype(np.uint8)
    color /= 255
    color[:, 3] = 1.0
    newcmp = ListedColormap(color)

    fig = plt.figure(figsize=(3, 6.0))
    ax = fig.add_axes((0.3, 0.1, 0.2, 0.8))

    cb1 = mpl.colorbar.ColorbarBase(ax, cmap=newcmp,
                                    extend='both',
                                    orientation='vertical')
    cb1.ax.set_title(title, loc='center')
    cb1.set_ticks(np.linspace(0, 1, len(labels), endpoint=True))
    cb1.set_ticklabels(labels)
    plt.savefig(dst)
    plt.close(fig=fig)
    return None


def main(src, dst):
    plt.rcParams['font.sans-serif'] = ['SimHei']
    plt.rcParams['axes.unicode_minus'] = False
    # 打开影像
    src_ds = gdal.Open(src)
    xsize = src_ds.RasterXSize
    ysize = src_ds.RasterYSize
    geo = src_ds.GetGeoTransform()
    prj = src_ds.GetProjection()
    src_array = src_ds.ReadAsArray()
    # 赋予颜色
    color = np.zeros((3, ysize, xsize), dtype=np.uint8)
    breakpoints = list(colormap.keys())
    for ichanel in range(3):
        for ibreak in range(len(breakpoints) - 1):
            breakpoint1 = breakpoints[ibreak]
            breakpoint2 = breakpoints[ibreak + 1]
            color1 = colormap[breakpoint1][ichanel]
            color2 = colormap[breakpoint2][ichanel]
            # 创建拉伸方程
            temp_index = np.where((src_array >= breakpoint1) & (src_array < breakpoint2))
            color[ichanel, temp_index[0], temp_index[1]] = (
                    (src_array[temp_index] - breakpoint1) * (color2 - color1) / (
                    breakpoint2 - breakpoint1) + color1).astype(np.uint8)
    # 创建结果影像
    drv = gdal.GetDriverByName('GTiff')
    basename = os.path.splitext(os.path.basename(src))[0]
    dst_file = os.path.join(dst, basename) + '_color.tif'
    out_ds = drv.Create(dst_file, xsize, ysize, 3, gdal.GDT_Byte)
    out_ds.SetGeoTransform(geo)
    out_ds.SetProjection(prj)
    for iband in range(3):
        band = out_ds.GetRasterBand(iband + 1)
        band.WriteArray(color[iband, :, :])
        band.FlushCache()
    out_ds = src_ds = None
    # 生成配套的colorbar
    dst_colorbar = os.path.join(dst, basename) + '_colorbar.png'
    title = '土壤旱情'
    colorbar_labels = ["特旱", "重旱", "中旱", "轻旱", "无旱"]
    color_bar(dst_colorbar, colorbar_labels, title)
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
    src_file = r"\\192.168.0.234\nydsj\user\ZSS\20210422test\L2A_T50SKE_20201103_ndvi_shiqiao.tif"
    dst_file = r"\\192.168.0.234\nydsj\user\ZSS\20210422test"
    main(src_file, dst_file)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
