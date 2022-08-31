#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2022/05/12 10:37
# @Author  : zhaoss
# @FileName: create_shp.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:

Parameters

"""
import os
import time
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def main(txt, shp):
    # 获取原始信息
    fj = open(txt, 'r', encoding='utf-8')
    lines = fj.readlines()
    # 定义目标投影
    oSRS = osr.SpatialReference()
    oSRS.SetWellKnownGeogCS("WGS84")
    # 创建点矢量
    shp_drv = ogr.GetDriverByName('ESRI Shapefile')
    shp_ds = shp_drv.CreateDataSource(shp)
    outLayer = shp_ds.CreateLayer(' ', geom_type=ogr.wkbPoint, srs=oSRS)
    # 为结果shp添加新字段信息
    coord_fld = ogr.FieldDefn('city', ogr.OFTString)
    coord_fld.SetWidth(10)
    outLayer.CreateField(coord_fld)
    coord_fld = ogr.FieldDefn('name', ogr.OFTString)
    outLayer.CreateField(coord_fld)
    # 创建虚拟要素用以输出
    out_defn = outLayer.GetLayerDefn()
    out_feat = ogr.Feature(out_defn)
    for line in lines:
        data = line.split()
        lat = float(data[3])
        lon = float(data[2])
        city = data[1]
        name = data[0]
        feat = ogr.Geometry(ogr.wkbPoint)
        feat.AddPoint(lon, lat)
        out_feat.SetGeometry(feat.Clone())
        out_feat.SetField('city', city)
        out_feat.SetField('name', name)
        outLayer.CreateFeature(out_feat)
    shp_ds.SyncToDisk()
    shp_ds = None
    fj.close()

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
    txt_path = r"F:\test\shp\test.txt"
    shp_path = r"F:\test\shp\test.shp"
    main(txt_path, shp_path)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
