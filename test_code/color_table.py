#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import glob
import numpy as np
import time
from osgeo import gdal


def color(infile, outfile, color_table):
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
    # dest_ds = gtiff_driver.Create(outfile, in_band.XSize, in_band.YSize, 2, gdal.GDT_Byte, ['ALPHA=YES'])
    dest_ds = gtiff_driver.Create(outfile, in_band.XSize, in_band.YSize, 1, gdal.GDT_Byte)
    dest_ds.SetProjection(prj)
    dest_ds.SetGeoTransform(geo)

    out_band1 = dest_ds.GetRasterBand(1)
    out_band1.SetNoDataValue(a_nodata)
    out_band1.WriteArray(in_band.ReadAsArray())
    # 写入颜色表
    colors = gdal.ColorTable()
    colors.SetColorEntry(0, color_table['xiaomai'])
    colors.SetColorEntry(1, color_table['qita'])
    colors.SetColorEntry(2, color_table['lindi'])

    out_band1.SetRasterColorTable(colors)

    # 设置透明度
    # data = out_band1.ReadAsArray()
    # data = np.where(data == 1, 0, 255)
    # data = np.where(data == 2, 0, 255)
    # dest_ds.GetRasterBand(2).WriteArray(data)
    # dest_ds.GetRasterBand(2).SetRasterColorInterpretation(gdal.GCI_AlphaBand)


    source_ds = None
    dest_ds = None


def main(infile, outfile, colortable):
    color(infile, outfile, colortable)


if __name__ == '__main__':
    start_time = time.clock()
    infile = r'\\192.168.0.234\nydsj\project\9.Insurance_gongyi\4.class_result\2.image\1.class\1.xiaomai\planet_8band_gongyi_class3_dlgq.tif'
    outfile = r'\\192.168.0.234\nydsj\user\ZSS\planet_8band_gongyi_class3_color.tif'
    if os.path.exists(outfile):
        os.remove(outfile)
    color_table = {'xiaomai': (255, 255, 0),
                   'putao': (140, 0, 255),
                   'lindi': (255, 255, 255),
                   'qita': (255, 255, 255)}
    main(infile, outfile, color_table)
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
