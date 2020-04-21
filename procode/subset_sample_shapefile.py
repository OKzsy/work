#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/2/15 16:16
# @Author  : zhaoss
# @FileName: subset_sample_shapefile.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
    对栅格分要素裁剪
Parameters
    参数1：输入影像
    参数2：用于裁剪的矢量
    参数3：裁剪结果输出路径
"""

import os
import sys
import glob
import re
import numpy as np
import time
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def rpj_vec(lyr, srs):
    """对矢量进行投影变换"""
    # 创建临时矢量文件
    mem_dri = ogr.GetDriverByName('Memory')
    mem_ds = mem_dri.CreateDataSource(' ')
    outLayer = mem_ds.CreateLayer(' ', geom_type=lyr.GetGeomType(), srs=srs)
    # 附加字段
    outLayer.CreateFields(lyr.schema)
    # 逐要素进行投影转换
    out_feat = ogr.Feature(outLayer.GetLayerDefn())
    for in_feat in lyr:
        geom = in_feat.geometry().Clone()
        geom.TransformTo(srs)
        out_feat.SetGeometry(geom)
        # 写入属性信息
        for i in range(in_feat.GetFieldCount()):
            out_feat.SetField(i, in_feat.GetField(i))
        outLayer.CreateFeature(out_feat)
    return mem_ds, outLayer


def Feature_memory_shp(feat, sr):
    """将指定的geometry导出为内存中单独的shpfile"""
    fid = feat.GetFID()
    # 在内存中创建临时的矢量文件，用以存储单独的要素
    # 创建临时矢量文件
    mem_dri = ogr.GetDriverByName('Memory')
    mem_ds = mem_dri.CreateDataSource(' ')
    outLayer = mem_ds.CreateLayer(' ', geom_type=ogr.wkbPolygon, srs=sr)
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


def shp2raster(raster_ds, shp_layer, ext):
    # 将行列整数浮点化
    ext = np.array(ext) * 1.0
    # 获取栅格数据的基本信息
    raster_prj = raster_ds.GetProjection()
    raster_geo = raster_ds.GetGeoTransform()
    # 根据最小重叠矩形的范围进行矢量栅格化
    ulx, uly = gdal.ApplyGeoTransform(raster_geo, ext[0], ext[1])
    x_size = ext[2] - ext[0]
    y_size = ext[3] - ext[1]
    # 创建mask
    # out = r"F:\test_data\clipraster\gdal_mask2\test3.tif"
    # mask_ds = gdal.GetDriverByName('GTiff').Create(out, int(x_size), int(y_size), 1, gdal.GDT_Byte)
    mask_ds = gdal.GetDriverByName('MEM').Create('', int(x_size), int(y_size), 1, gdal.GDT_Byte)
    mask_ds.SetProjection(raster_prj)
    mask_geo = [ulx, raster_geo[1], 0, uly, 0, raster_geo[5]]
    mask_ds.SetGeoTransform(mask_geo)
    # 矢量栅格化
    gdal.RasterizeLayer(mask_ds, [1], shp_layer, burn_values=[1])
    return mask_ds


def min_rect(raster_ds, shp_layer):
    # 获取栅格的大小
    x_size = raster_ds.RasterXSize
    y_size = raster_ds.RasterYSize
    # 获取是矢量的范围
    extent = shp_layer.GetExtent()
    # 获取栅格的放射变换参数
    raster_geo = raster_ds.GetGeoTransform()
    # 计算逆放射变换系数
    raster_inv_geo = gdal.InvGeoTransform(raster_geo)
    # 计算在raster上的行列号
    # 左上
    off_ulx, off_uly = map(round, gdal.ApplyGeoTransform(raster_inv_geo, extent[0], extent[3]))
    # 右下
    off_drx, off_dry = map(round, gdal.ApplyGeoTransform(raster_inv_geo, extent[1], extent[2]))
    # 判断是否有重叠区域
    if off_ulx >= x_size or off_uly >= y_size or off_drx <= 0 or off_dry <= 0:
        return 0
    # 限定重叠范围在栅格影像上
    # 列
    offset_column = np.array([off_ulx, off_drx])
    offset_column = np.maximum((np.minimum(offset_column, x_size - 1)), 0)
    # 行
    offset_line = np.array([off_uly, off_dry])
    offset_line = np.maximum((np.minimum(offset_line, y_size - 1)), 0)
    if offset_column[1] == offset_column[0]:
        offset_column[1] += 1
    if offset_line[1] == offset_line[0]:
        offset_line[1] += 1
    return [offset_column[0], offset_line[0], offset_column[1], offset_line[1]]


def mask_raster(raster_ds, mask_ds, outfile, ext):
    # 将行列整数浮点化
    ext = np.array(ext) * 1.0
    # 获取栅格数据的基本信息
    raster_prj = raster_ds.GetProjection()
    raster_geo = raster_ds.GetGeoTransform()
    bandCount = raster_ds.RasterCount
    dataType = raster_ds.GetRasterBand(1).DataType
    # 根据最小重叠矩形的范围进行矢量栅格化
    ulx, uly = gdal.ApplyGeoTransform(raster_geo, ext[0], ext[1])
    x_size = ext[2] - ext[0]
    y_size = ext[3] - ext[1]
    # 创建输出影像
    result_ds = gdal.GetDriverByName('GTiff').Create(outfile, int(x_size), int(y_size), bandCount, dataType)
    result_ds.SetProjection(raster_prj)
    result_geo = [ulx, raster_geo[1], 0, uly, 0, raster_geo[5]]
    result_ds.SetGeoTransform(result_geo)
    # 获取掩模
    mask = mask_ds.GetRasterBand(1).ReadAsArray()
    mask = 1 - mask
    # 对原始影像进行掩模并输出
    for band in range(bandCount):
        banddata = raster_ds.GetRasterBand(band + 1).ReadAsArray(int(ext[0]), int(ext[1]), int(x_size), int(y_size))
        banddata = np.choose(mask, (banddata, 0))
        result_ds.GetRasterBand(band + 1).WriteArray(banddata)
    return 1


def main(raster, shp, out, fieldName):
    if fieldName == None:
        fieldName = 'Name'
    # 打开栅格和矢量影像
    raster_ds = gdal.Open(raster)
    raster_basename = os.path.splitext(os.path.basename(raster))[0]
    shp_ds = ogr.Open(shp)
    shp_lyr = shp_ds.GetLayer()
    shp_sr = shp_lyr.GetSpatialRef()
    # 判断栅格和矢量的投影是否一致，不一致进行矢量投影变换
    raster_srs_wkt = raster_ds.GetProjection()
    raster_srs = osr.SpatialReference()
    raster_srs.ImportFromWkt(raster_srs_wkt)
    # 判断两个SRS的基准是否一致
    if not shp_sr.IsSameGeogCS(raster_srs):
        sys.exit("两个空间参考的基准面不一致，不能进行投影转换！！！")
    # 判断两个SRS是否一致
    elif shp_sr.IsSame(raster_srs):
        re_shp_l = shp_lyr
        shp_lyr = None
    else:
        re_shp_ds, re_shp_l = rpj_vec(shp_lyr, raster_srs)
    # 拆分矢量用以对单个要素进行裁剪
    # 定义变量用以显示进度条
    count = 0
    num_feature = re_shp_l.GetFeatureCount()
    # 打开栅格影像
    for feat in re_shp_l:
        progress((count + 1) / num_feature)
        count += 1
        outdir = out
        outpath = os.path.join(outdir, raster_basename + '_' + feat.GetField(fieldName) + '.tif')
        # 要素提取为图层
        feat_ds, feat_lyr = Feature_memory_shp(feat, raster_srs)
        # 要素裁剪
        # 计算矢量和栅格的最小重叠矩形
        offset = min_rect(raster_ds, feat_lyr)
        # 判断是否有重叠区域，如无（0），则跳过
        if offset == 0:
            continue
        # 矢量栅格化
        mask_ds = shp2raster(raster_ds, feat_lyr, offset)
        # 进行裁剪
        res = mask_raster(raster_ds, mask_ds, outpath, offset)
    re_shp_ds = None
    raster_ds = None
    shp_ds = None
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
    # if len(sys.argv[1:]) < 3:
    #     sys.exit('Problem reading input')
    # main(sys.argv[1], sys.argv[2], sys.argv[3])
    in_file = r"\\192.168.0.234\nydsj\user\ZSS\农保项目\S2\62xianque_out\res\L2A_T50SKC_A021665_20190816T031414_ref_10m-prj.tif"
    shpfile = r"\\192.168.0.234\nydsj\user\遥感院\农保项目\深度学习\S2\land_L2A_T50SKC_A021665_20190816T031414.shp"
    outfile = r"\\192.168.0.234\nydsj\user\LXX\协助他人\农保\clip\use"
    # if len(sys.argv[1:]) < 4:
    #     sys.exit('Problem reading input')
    # in_file = sys.argv[1]
    # shpfile = sys.argv[2]
    # outfile = sys.argv[3]
    # field_name = sys.argv[4]
    # if len(field_name) == 0:
    #     field_name = None
    field_name = None
    main(in_file, shpfile, outfile, field_name)
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
