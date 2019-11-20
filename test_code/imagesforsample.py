#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/7/16 16:01
# @Author  : zhaoss
# @FileName: imagesforsample.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import glob
import sys
import os
import time
import numpy as np
import xml.dom.minidom as xml_mini
from osgeo import gdal, ogr, osr, gdalconst
from ospybook.vectorplotter import VectorPlotter

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress

def main(sample_shp, img_shp, description=None):
    if description == None:
        sys.exit("缺少‘描述’ 程序不能运行！")
    vp = VectorPlotter(False)
    # 打开样本矢量
    sample_ds = ogr.Open(sample_shp, 1)
    sample_lyr = sample_ds.GetLayer(0)
    # 打开影像矢量
    image_ds = ogr.Open(img_shp)
    img_lyr = image_ds.GetLayer(0)
    # 过滤描述信息
    # sample_lyr.SetAttributeFilter('描述 = {}'.format(description))
    sample_lyr.ResetReading()
    sample_lyr.SetAttributeFilter("despict = {}".format("'" + description + "'"))
    count = 1
    total = sample_lyr.GetFeatureCount()
    for feat in sample_lyr:
        geom = feat.geometry().Clone()
        # 对影像矢量进行筛选
        img_lyr.ResetReading()
        img_lyr.SetSpatialFilter(geom)
        imgforfeat = []
        for img_feat in img_lyr:
            # 获取属性
            img_name = img_feat.GetField('browsefile')
            img_names = os.path.splitext(os.path.basename(img_name))[0].split("_")
            name_id = "_".join([img_names[0], img_names[4], img_names[5]])
            imgforfeat.append(name_id)
        img_lyr.SetSpatialFilter(None)
        str_name = "/".join(imgforfeat)
        feat.SetField('image', str_name)
        sample_lyr.SetFeature(feat)
        progress(count / total)
        count += 1
    sample_lyr.SetAttributeFilter(None)
    return None


if __name__ == '__main__':
    start_time = time.clock()
    # 支持中文路径
    gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
    # 支持中文属性字段
    gdal.SetConfigOption("SHAPE_ENCODING", "GBK")
    # 注册所有ogr驱动
    ogr.RegisterAll()
    # 注册所有gdal驱动
    gdal.AllRegister()
    sample_shp = r"\\192.168.0.234\nydsj\user\ZSS\20190716test\land_安阳_鹤壁_商丘.shp"
    img_shp = r"\\192.168.0.234\nydsj\user\ZSS\20190716test\GF2_高覆盖度草地.shp"
    description = "中覆盖度草地"
    main(sample_shp, img_shp, description)
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))


