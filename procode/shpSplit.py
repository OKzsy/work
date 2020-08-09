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


def filter_spatial_disk_shp(vec_lyr, out_dir, filter_lyr, fieldName):
    """
    根据空间范围裁剪另一个矢量
    :param vec_lyr:
    :param out_dir:
    :param filter_lyr:
    :param fieldName:
    :return:
    """
    for feat in filter_lyr:
        geom = feat.geometry().Clone()
        out_path = os.path.join(out_dir, feat.GetField(fieldName)) + '.shp'
        # 创建输出矢量
        driver = ogr.GetDriverByName('ESRI Shapefile')
        out_ds = driver.CreateDataSource(out_path)
        vec_lyr.SetSpatialFilter(geom)
        out_ds.CopyLayer(vec_lyr, 'new_layer')
        out_ds.SyncToDisk()
        vec_lyr.SetSpatialFilter(None)
    return None


def export_fea_memory_shp(vec_lyr, Fid):
    """将geometry导出为内存中单独的shpfile,并保留原来的属性"""
    feat = vec_lyr.GetFeature(Fid)
    fid = feat.GetFID()
    # 在内存中创建临时的矢量文件，用以存储单独的要素
    # 创建临时矢量文件
    mem_dri = ogr.GetDriverByName('Memory')
    mem_ds = mem_dri.CreateDataSource(' ')
    outLayer = mem_ds.CreateLayer(' ', geom_type=vec_lyr.GetGeomType(),
                                  srs=vec_lyr.GetSpatialRef())
    # 给图层中创建字段用以标识原来的FID
    coor_fld = ogr.FieldDefn(vec_lyr.schema)
    outLayer.CreateField(coor_fld)
    # 创建虚拟要素，用以填充原始要素
    out_defn = outLayer.GetLayerDefn()
    out_feat = ogr.Feature(out_defn)
    # 对字段填充值
    for i in range(feat.GetFieldCount()):
        value = feat.GetField(i)
        out_feat.SetField(i, value)
    # 填充要素
    out_feat.SetGeometry(feat.geometry())
    outLayer.CreateFeature(out_feat)
    return mem_ds, outLayer


def filter_attri_disk_shp(vec_lyr, out_path, filter_str):
    """
    将指定属性的面导出为磁盘中的shpfile
    :param vec_lyr:
    :param out_path:
    :param filter_str:
        filter_str = '\"{}\" = {}'.format('分区', "'" + '实验区' + "'")
        filter_str = '\"{}\" > {}'.format('num', 2.2)
    :return:
    """
    # 创建输出矢量
    driver = ogr.GetDriverByName('ESRI Shapefile')
    out_ds = driver.CreateDataSource(out_path)
    vec_lyr.SetAttributeFilter(filter_str)
    out_ds.CopyLayer(vec_lyr, 'test_out')
    out_ds.SyncToDisk()


def Feature_disk_shp(vec_lyr, out_shp, Fid):
    """将指定的geometry导出为磁盘中单独的shpfile"""
    # 创建输出矢量
    driver = ogr.GetDriverByName('ESRI Shapefile')
    out_ds = driver.CreateDataSource(out_shp)
    outLayer = out_ds.CreateLayer("test_layer", geom_type=vec_lyr.GetGeomType(),
                                  srs=vec_lyr.GetSpatialRef())
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
    outLayer = mem_ds.CreateLayer(' ', geom_type=vec_lyr.GetGeomType(),
                                  srs=vec_lyr.GetSpatialRef())
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


def main(in_vec, out_dir):
    # 打开原始矢量数据
    filter_shp = r"\\192.168.0.234\nydsj\project\2.zhiyan\3.2020\1.vector\1.xzqh\镇\洛阳\伊川县.shp"
    in_vec_ds = ogr.Open(in_vec)
    in_lyr = in_vec_ds.GetLayer(0)
    filter_ds = ogr.Open(filter_shp)
    filter_lyr = filter_ds.GetLayer(0)
    # out_ds, out_lyr = Feature_memory_shp(in_lyr, fid)
    # driver = in_vec_ds.GetDriver()
    # driver.CopyDataSource(out_ds, out_vec)
    # del out_ds
    # Feature_disk_shp(in_lyr, out_vec, fid)
    # filter_str = '\"{}\" = {}'.format('分区', "'" + '实验区' + "'")
    # filter_str = '\"{}\" > {}'.format('num', 2.2)
    # filter_attri_disk_shp(in_lyr, out_vec, filter_str)
    filter_spatial_disk_shp(in_lyr, out_dir, filter_lyr, 'name')

if __name__ == '__main__':
    # 支持中文路径
    gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
    # 支持中文属性字段
    gdal.SetConfigOption("SHAPE_ENCODING", "gb2312")
    # 注册所有ogr驱动
    ogr.RegisterAll()

    start_time = time.clock()

    src_shp = r"\\192.168.0.234\nydsj\user\LXX\烟草2020\dk\yichuan.shp"
    dst_shp = r"\\192.168.0.234\nydsj\shp"
    main(src_shp, dst_shp)
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
