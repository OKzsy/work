#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/2/15 15:01
# @Author  : zhaoss
# @FileName: shpSplit.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import glob
import time
from osgeo import gdal, ogr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def Feature_disk_shp(vec_lyr, out_path, Fid):
    """将指定的geometry导出为磁盘中单独的shpfile"""
    # 创建输出矢量
    driver = ogr.GetDriverByName('ESRI Shapefile')
    out_ds = driver.CreateDataSource(out_shp)
    outLayer = out_ds.CreateLayer("test_layer", geom_type=vec_lyr.GetGeomType(), srs=vec_lyr.GetSpatialRef())
    coor_fld = ogr.FieldDefn('ID_FID', ogr.OFTInteger)
    outLayer.CreateField(coor_fld)
    # 插入要素
    feat = vec_lyr.GetFeature(Fid)
    fid = feat.GetFID()
    fld_index = outLayer.GetLayerDefn().GetFieldIndex('ID_FID')
    feat.SetField(fld_index, fid)
    outLayer.CreateFeature(feat)
    out_ds.SyncToDisk()


def Feature_memory_shp(vec_lyr, Fid):
    """将指定的geometry导出为内存中单独的shpfile"""
    feat = vec_lyr.GetFeature(Fid)
    fid = feat.GetFID()
    # 在内存中创建临时的矢量文件，用以存储单独的要素
    # 创建临时矢量文件
    mem_dri = ogr.GetDriverByName('Memory')
    mem_ds = mem_dri.CreateDataSource(' ')
    outLayer = mem_ds.CreateLayer(' ', geom_type=vec_lyr.GetGeomType(), srs=vec_lyr.GetSpatialRef())
    # 给图层中创建字段用以标识原来的FID
    coor_fld = ogr.FieldDefn('ID_FID', ogr.OFTInteger)
    outLayer.CreateField(coor_fld)
    # 创建虚拟要素，用以填充原始要素
    out_defn = outLayer.GetLayerDefn()
    out_feat = ogr.Feature(out_defn)
    # 对ID_FID字段填充值
    fld_index = outLayer.GetLayerDefn().GetFieldIndex('ID_FID')
    out_feat.SetField(fld_index, fid)
    # 填充要素
    out_feat.SetGeometry(feat.geometry())
    outLayer.CreateFeature(out_feat)
    return mem_ds, outLayer


def main(in_vec, out_vec, fid):
    # 打开原始矢量数据
    in_vec_ds = ogr.Open(in_vec)
    in_lyr = in_vec_ds.GetLayer(0)
    # out_ds, out_lyr = Feature_memory_shp(in_lyr, fid)
    # driver = in_vec_ds.GetDriver()
    # driver.CopyDataSource(out_ds, out_vec)
    # del out_ds
    Feature_disk_shp(in_lyr, out_vec, fid)


if __name__ == '__main__':
    # 支持中文路径
    gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "NO")
    # 支持中文属性字段
    gdal.SetConfigOption("SHAPE_ENCODING", "")
    # 注册所有ogr驱动
    ogr.RegisterAll()

    start_time = time.clock()

    shp_path = r"F:\ChangeMonitoring\UTM\sample_project.shp"
    out_shp = r"F:\ChangeMonitoring\UTM\test.shp"
    FID = 10
    main(shp_path, out_shp, FID)
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
