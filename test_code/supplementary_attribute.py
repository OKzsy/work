#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/3/21 10:03
# @Author  : zhaoss
# @FileName: supplementary_attribute.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import glob
import time
import openpyxl as xl
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def main(shp, excel):
    # 打开shp
    shp_ds = ogr.Open(shp, 1)
    lyr = shp_ds.GetLayer(0)
    # 打开excel
    wb = xl.load_workbook(excel)
    ws = wb.active
    # 获取要填充的属性字段在是俩个中的位置
    index = lyr.GetLayerDefn().GetFieldIndex('level4')
    # 定义变量用以显示进度条
    count = 0
    num_feature = lyr.GetFeatureCount()
    lyr.ResetReading()
    for feat in lyr:
        # 获取该要素的XZQDM
        xzqdm = feat.XZQDM[0:9]
        for row in ws.iter_rows():
            xzdm = str(row[0].value)
            if xzqdm == xzdm:
                # 获取对应的镇名
                zm = row[2].value
                # 更新到矢量属性中
                feat.SetField(index, zm)
                lyr.SetFeature(feat)
                break
            else:
                continue
        progress((count + 1) / num_feature)
        count += 1
    shp_ds.SyncToDisk()
    shp_ds = None
    wb = None
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
    shp_path = r"\\192.168.0.234\nydsj\common\1.vector\1.xzqh\C_河南省.shp"
    excel_path = r"F:\test_data\河南省乡镇行政区划.xlsx"
    main(shp_path, excel_path)
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
