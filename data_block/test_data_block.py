#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/8/9 17:04
# @Author  : zhaoss
# @FileName: data_block.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import glob
import sys
import time
import fnmatch
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst


from datablock import DataBlock

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def block(overlap_line, totalblocknum, IDblock, linesblock, xsize, ysize):
    """
    根据数据信息，计算指定块的起始行数和对应的总行列数
    :param overlap_line: 块与块之间的重叠行数
    :param totalblocknum: 该影像总共分多少块
    :param IDblock: 某一个指定块的编号, 且必须从0开始
    :param linesblock: 每个块的行数
    :param ysize: 该影像总行数
    :return:
    """
    # 根据数据块顺序计算该块的起始 - 结尾行号
    # IDblock = IDblock - 1
    # 需要特别处理最后一块，因此判断是否该进程处理的是最后一块
    # if IDblock == totalblocknum - 1:
    if linesblock < overlap_line:
        sys.exit("The overlap line can't less than the lines in per block!")
    if IDblock == 0:
        # 判断块的行数是否大于总行数
        if linesblock >= ysize:
            linesblock = ysize - overlap_line
        # 该块的起始行号
        xs_col = 0
        ys_line = 0
        rows = linesblock + overlap_line
        columns = xsize
        tile_get = [xs_col, ys_line, columns, rows]
        ye_line = overlap_line > 0 and -overlap_line or rows
        tile_put = [0, ye_line, xs_col, ys_line]
        return tile_get, tile_put
    elif IDblock == totalblocknum - 1:
        # 该块的起始行列号
        xs_col = 0
        ys_line = IDblock * linesblock - overlap_line
        rows = ysize - IDblock * linesblock + overlap_line
        columns = xsize
        tile_get = [xs_col, ys_line, columns, rows]
        tile_put = [overlap_line, rows, xs_col, ys_line + overlap_line]
        return tile_get, tile_put
    else:
        # 该块的起始行列号
        xs_col = 0
        ys_line = IDblock * linesblock - overlap_line
        rows = linesblock + overlap_line * 2
        columns = xsize
        tile_get = [xs_col, ys_line, columns, rows]
        ye_line = overlap_line > 0 and -overlap_line or rows
        tile_put = [overlap_line, ye_line, xs_col, ys_line + overlap_line]
        return tile_get, tile_put


def main(in_file):
    # 打开影像
    img_ds = gdal.Open(in_file)
    # 获取影像的行数
    xsize = img_ds.RasterXSize
    ysize = img_ds.RasterYSize
    bandcount = img_ds.RasterCount
    # 创建输出影像
    out_img = r"F:\test_data\new_test\GF2_20190509_L1A0003988007P_out3.tif"
    driver = gdal.GetDriverByName('GTiff')
    out_ds = driver.Create(out_img, xsize, ysize, bandcount, gdal.GDT_UInt16)
    out_ds.SetProjection(img_ds.GetProjection())
    out_ds.SetGeoTransform(img_ds.GetGeoTransform())
    # 定义按照多少行分块
    # 引用DataBlock类
    img_block = DataBlock(xsize, ysize, 150, 3)
    numsblocks = img_block.numsblocks
    for IDblock in range(numsblocks):
        dims_get, dims_put = img_block.block(IDblock)
        # 分块度如和写出
        for iband in range(bandcount):
            temp_arr = img_ds.GetRasterBand(iband + 1).ReadAsArray(dims_get[0], dims_get[1], dims_get[2], dims_get[3])
            out_ds.GetRasterBand(iband + 1).WriteArray(temp_arr[dims_put[0]: dims_put[1], :], dims_put[2], dims_put[3])
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
    start_time = time.clock()
    in_file = r"F:\test_data\new_test\GF2_20190509_L1A0003988007P_sha.tiff"
    end_time = time.clock()
    main(in_file)
    print("time: %.4f secs." % (end_time - start_time))
