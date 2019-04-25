#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/2/22 15:31
# @Author  : zhaoss
# @FileName: reprojectVector.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import sys
import glob
import time
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def rpj_vec(lay, outfile, srs):
    # 创建输出矢量文件
    shp_driver = ogr.GetDriverByName('ESRI Shapefile')
    out_ds = shp_driver.CreateDataSource(outfile)
    out_lay = out_ds.CreateLayer('Polygon', srs=srs, geom_type=ogr.wkbPolygon)
    # 附加字段
    out_lay.CreateFields(lay.schema)
    # 逐要素进行投影转换
    out_feat = ogr.Feature(out_lay.GetLayerDefn())
    for in_feat in lay:
        geom = in_feat.geometry().Clone()
        geom.TransformTo(srs)
        out_feat.SetGeometry(geom)
        # 写入属性信息
        for i in range(in_feat.GetFieldCount()):
            out_feat.SetField(i, in_feat.GetField(i))
        out_lay.CreateFeature(out_feat)
    out_ds.SyncToDisk()
    return None


def main(infile, outfile, sr):
    # 打开原矢量文件
    in_ds = ogr.Open(infile)
    in_lay = in_ds.GetLayer(0)
    # 获取原始SRS的WTK
    in_sr = in_lay.GetSpatialRef()
    # 根据ESPG获取输出的SRS
    out_sr = osr.SpatialReference()
    out_sr.ImportFromEPSG(sr)
    # 判断两个SRS的基准是否一致
    if not in_sr.IsSameGeogCS(out_sr):
        sys.exit("两个空间参考的基准面不一致，不能进行投影转换！！！")
    # 判断两个SRS是否一致
    elif in_sr.IsSame(out_sr):
        sys.exit("两个空间参考一致，不需进行投影变换！！！")
    else:
        rpj_vec(in_lay, outfile, out_sr)
    in_ds = None
    return None


if __name__ == '__main__':
    gdal.UseExceptions()
    # 注册gdal的驱动
    gdal.AllRegister()
    # 注册ogr的驱动
    ogr.RegisterAll()
    gdal.SetConfigOption("gdal_FILENAME_IS_UTF8", "YES")  # 支持中文路径“YES”
    gdal.SetConfigOption("SHAPE_ENCODING", "GBK")  # 支持中文属性字段
    start_time = time.clock()
    in_shp_file = r"F:\ChangeMonitoring\UTM\sample_project.shp"
    out_shp_file = r"F:\ChangeMonitoring\UTM\test.shp"
    out_srs = 4326

    main(in_shp_file, out_shp_file, out_srs)

    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
