#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/2/15 16:16
# @Author  : zhaoss
# @FileName: subset_via_shapefile.py
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
import numpy as np
import time
from osgeo import gdal, ogr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


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


def main(raster, shp, out):
    # 打开栅格和矢量影像
    raster_ds = gdal.Open(raster)
    shp_ds = ogr.Open(shp)
    shp_l = shp_ds.GetLayer()
    sr = shp_l.GetSpatialRef()
    # 拆分矢量用以对单个要素进行裁剪
    # 定义变量用以显示进度条
    count = 0
    num_feature = shp_l.GetFeatureCount()
    for feat in shp_l:
        # 获取要素的属性值用以确定输出tif影像的名字和路径
        outdir = os.path.join(out, feat.Name.split('-')[1])
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        outpath = os.path.join(outdir, feat.Name + '.tiff')
        # 要素提取为图层
        feat_ds, feat_lyr = Feature_memory_shp(feat, sr)
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
        progress(count + 1 / num_feature)
        count += 1
    return None


if __name__ == '__main__':
    # 支持中文路径
    gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "NO")
    # 支持中文属性字段
    gdal.SetConfigOption("SHAPE_ENCODING", "")
    # 注册所有ogr驱动
    ogr.RegisterAll()
    # 注册所有gdal驱动
    gdal.AllRegister()

    start_time = time.clock()
    in_file = r"F:\ChangeMonitoring\huijiqu\L2A_T49SGU_A018376_20181229T031726_ref_10m.tif"
    shpfile = r"F:\ChangeMonitoring\UTM\sample_project.shp"
    outfile = r"F:\ChangeMonitoring\sample\12"
    main(in_file, shpfile, outfile)
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
