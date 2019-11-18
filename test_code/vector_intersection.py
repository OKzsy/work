#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/7/3 16:21
# @Author  : zhaoss
# @FileName: vector_intersection.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import glob
import time
import numpy as np
import xml.dom.minidom as xml_mini
from osgeo import gdal, ogr, osr, gdalconst
from ospybook.vectorplotter import VectorPlotter

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress

def vector_interstction(geometry, flag, lyr):
    for ifeat in lyr:
        if ifeat.GetField('OBJECTID') in flag:
            continue

    return 1
def main(sample_shp1, out_shp):
    vp = VectorPlotter(False)
    water_ds = ogr.Open(sample_shp1)
    water_lyr = water_ds.GetLayer(0)
    # 准备输出的shp
    out_shp_ds = water_ds.GetDriver().CreateDataSource(out_shp)
    out_lyr = out_shp_ds.CreateLayer('category', srs=water_lyr.GetSpatialRef(), geom_type=water_lyr.GetGeomType())
    # 写入属性字段
    out_lyr.CreateFields(water_lyr.schema)
    # 新增字段
    coor_fld = ogr.FieldDefn('相交面', ogr.OFTString)
    coor_fld.SetWidth(50)
    out_lyr.CreateField(coor_fld)
    coor_fld.SetName("总品类")
    out_lyr.CreateField(coor_fld)
    # 创建初始要素
    out_defn = out_lyr.GetLayerDefn()
    out_feat = ogr.Feature(out_defn)

    mem_dri = ogr.GetDriverByName('Memory')
    mem_ds = mem_dri.CreateDataSource(' ')
    temp_lyr = mem_ds.CopyLayer(water_lyr, 'temp_lyr')
    water_lyr.ResetReading()
    for feat in water_lyr:
        geometry = feat.geometry().Clone()
        temp_lyr.SetSpatialFilter(geometry)
        for freq in range(temp_lyr.GetFeatureCount() - 1):
            pass







        # 拷贝feat
        category = new_feat.GetField('地类')
        objectid = new_feat.GetField('OBJECTID')
        for i in range(new_feat.GetFieldCount()):
            value = feat.GetField(i)
            out_feat.SetField(i, value)
        out_feat.SetField(out_feat.GetFieldCount() - 2, objectid)
        out_feat.SetField(out_feat.GetFieldCount() - 1, category)
        out_feat.SetGeometry(geometry)
        out_lyr.CreateFeature(out_feat)
        objectids = []
        categorys = []
        intersection_geom = []
        intersection_geom_temp = []
        objectids.append(str(objectid))
        categorys.append(category)
        intersection_geom_temp.append(geometry.Clone())

        for igeom in intersection_geom:
            for new_feat in temp_lyr:
                if new_feat.GetField('OBJECTID') in objectids:
                    continue
                category = new_feat.GetField('地类')
                objectid = new_feat.GetField('OBJECTID')
                new_geom = new_feat.geometry().Clone()
                intersection = new_geom.Intersection(geometry)
                if intersection.Area() != 0.0:
                    intersection_geom.append(intersection.Clone)
                    for i in range(new_feat.GetFieldCount()):
                        value = feat.GetField(i)
                        out_feat.SetField(i, value)
                    if category not in categorys:
                        categorys.append(category)
                    if objectid not in objectids:
                        objectids.append(str(objectid))
                    objectids.sort()
                    all_category = '/'.join(categorys)
                    all_objectid = '/'.join(objectids)

                    geometry = intersection.Clone()
                    out_feat.SetField(out_feat.GetFieldCount() - 2, all_objectid)
                    out_feat.SetField(out_feat.GetFieldCount() - 1, all_category)
                    out_feat.SetGeometry(intersection)
                    out_lyr.CreateFeature(out_feat)
            temp_lyr.SetSpatialFilter(None)
    out_shp_ds.SyncToDisk()
    out_shp_ds = None

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
    in_sample_shp1 = r"\\192.168.0.234\nydsj\user\ZSS\20190626\Export_Output.shp"
    out_shp = r"\\192.168.0.234\nydsj\user\ZSS\20190626\Output1.shp"
    main(in_sample_shp1, out_shp)
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))


