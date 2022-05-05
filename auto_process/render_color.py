#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2021/3/23 16:46
# @Author  : zhaoss
# @FileName: render_color.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description：
根据输入颜色,对生成的指数黑白图像进行颜色渲染，同时创建对应的颜色条

Parameters


"""

import os
import time
import glob
import fnmatch
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.colors import ListedColormap
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress

# 确定颜色字典
# color_dict={split_point: [R, G, B]}
color_dict = {
    'first': [255, 167, 127],
    0.025: [163, 255, 115],
    0.094: [85, 255, 0],
    0.163: [76, 230, 0],
    0.218: [56, 168, 0],
    'last': [56, 168, 0],
}


def searchfiles(dirpath, partfileinfo='*', recursive=False):
    """列出符合条件的文件（包含路径），默认不进行递归查询，当recursive为True时同时查询子文件夹"""
    # 定义结果输出列表
    filelist = []
    # 列出根目录下包含文件夹在内的所有文件目录
    pathlist = glob.glob(os.path.join(os.path.sep, dirpath, "*"))
    # 逐文件进行判断
    for mpath in pathlist:
        if os.path.isdir(mpath):
            # 默认不判断子文件夹
            if recursive:
                filelist += searchfiles(mpath, partfileinfo, recursive)
        elif fnmatch.fnmatch(os.path.basename(mpath), partfileinfo):
            filelist.append(mpath)
        # 如果mpath为子文件夹，则进行递归调用，判断子文件夹下的文件

    return filelist


def color_bar(dst, labels, title, segment):
    # 生成colorbar颜色
    color = np.ones((256, 4))
    breakpoints = sorted([float(k) for k in list(color_dict.keys())])
    pos_list = [(breakpoints[k] + breakpoints[k + 1]) / 2 for k in range(len(breakpoints) - 1)]
    color_index = np.linspace(breakpoints[0], breakpoints[-1] - 0.01 * breakpoints[-1], 256)
    for ichanel in range(3):
        for ibreak in range(len(breakpoints) - 1):
            breakpoint1 = breakpoints[ibreak]
            breakpoint2 = breakpoints[ibreak + 1]
            color1 = color_dict[breakpoint1][ichanel] / 255
            color2 = color_dict[breakpoint2][ichanel] / 255
            if not segment:
                # 创建拉伸方程
                temp_index = np.where((color_index >= breakpoint1) & (color_index < breakpoint2))
                color[temp_index[0], ichanel] = (color_index[temp_index] - breakpoint1) * (color2 - color1) / (
                        breakpoint2 - breakpoint1) + color1
            else:
                # 使用离散颜色
                temp_index = np.where((color_index >= breakpoint1) & (color_index < breakpoint2))
                color[temp_index[0], ichanel] = color1
    color[:, 3] = 1.0
    newcmp = mpl.colors.ListedColormap(color)
    newcmp.set_under(color[0, :])
    newcmp.set_over(color[-1, :])
    norm = mpl.colors.Normalize(vmin=breakpoints[0], vmax=breakpoints[-1])
    fig, ax = plt.subplots(figsize=(1, 6), tight_layout=True)
    fig.subplots_adjust(left=0.25, right=0.75)
    cb1 = mpl.colorbar.ColorbarBase(ax, cmap=newcmp, norm=norm,
                                    ticks=np.array(pos_list),
                                    extend='both',
                                    orientation='vertical')
    ax.set_title(title, loc='center', pad=5)
    cb1.set_ticklabels(labels)
    fig.savefig(dst)
    plt.close(fig=fig)
    return None


def main(file, dst, nodata, title, labels, segment=False):
    plt.rcParams['font.sans-serif'] = ['SimHei']
    plt.rcParams['axes.unicode_minus'] = False
    # 判断输入的是否为文件
    if os.path.isdir(file):
        rasters = searchfiles(file, partfileinfo='*.tif')
    else:
        rasters = [file]
    # 打开影像
    for src in rasters:
        src_ds = gdal.Open(src)
        xsize = src_ds.RasterXSize
        ysize = src_ds.RasterYSize
        geo = src_ds.GetGeoTransform()
        prj = src_ds.GetProjection()
        src_array = src_ds.ReadAsArray()
        # 查找影像中的最大最小值（除去nodata之外）
        min_value = np.min(np.where(src_array == nodata, src_array.max(), src_array))
        max_value = np.max(np.where(src_array == nodata, min_value, src_array))
        max_value += 0.01 * max_value
        # 修改字典中第一个和最后一个颜色索引的间断点值
        color_dict[min_value] = color_dict.pop('first')
        color_dict[max_value] = color_dict.pop('last')
        # 赋予颜色
        color = np.zeros((3, ysize, xsize), dtype=np.uint8)
        breakpoints = sorted([float(k) for k in list(color_dict.keys())])
        for ichanel in range(3):
            for ibreak in range(len(breakpoints) - 1):
                breakpoint1 = breakpoints[ibreak]
                breakpoint2 = breakpoints[ibreak + 1]
                color1 = color_dict[breakpoint1][ichanel]
                color2 = color_dict[breakpoint2][ichanel]
                if not segment:
                    # 创建拉伸方程
                    temp_index = np.where((src_array >= breakpoint1) & (src_array < breakpoint2))
                    color[ichanel, temp_index[0], temp_index[1]] = (
                            (src_array[temp_index] - breakpoint1) * (color2 - color1) / (
                            breakpoint2 - breakpoint1) + color1).astype(np.uint8)
                else:
                    # 使用离散颜色
                    temp_index = np.where((src_array >= breakpoint1) & (src_array < breakpoint2))
                    color[ichanel, temp_index[0], temp_index[1]] = color1
                    pass
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
        color_bar(dst_colorbar, labels, title, segment)
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
    src_file = r"\\192.168.0.234\nydsj\user\ZSS\qixian_yanshi\test_clip\new"
    dst_file = r"\\192.168.0.234\nydsj\user\ZSS\qixian_yanshi\test_clip\new"
    nodata_value = -10
    colorbar_title = '小麦苗情'
    colorbar_labels = ["五等", "四等", "三等", "二等", "一等"]
    # 确定使用离散色还是连续色
    segment = False
    main(src_file, dst_file, nodata_value, colorbar_title, colorbar_labels, segment=segment)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
