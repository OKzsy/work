#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/7/31 18:19
# @Author  : zhaoss
# @FileName: clipforunet.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import glob
import time
import sys
import math
import numpy as np

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
    mask_ds = gdal.GetDriverByName('MEM').Create('', int(x_size), int(y_size), 1, gdal.GDT_Byte)
    mask_ds.SetProjection(raster_prj)
    mask_geo = [ulx, raster_geo[1], 0, uly, 0, raster_geo[5]]
    mask_ds.SetGeoTransform(mask_geo)
    # 矢量栅格化
    gdal.RasterizeLayer(mask_ds, [1], shp_layer, burn_values=[1])
    return mask_ds


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
        sys.exit("Have no overlap")
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
    # 对原始影像进行掩模并输出
    nodata = 0
    for band in range(bandCount):
        banddata = raster_ds.GetRasterBand(band + 1).ReadAsArray(int(ext[0]), int(ext[1]), int(x_size), int(y_size))
        banddata = np.choose(mask, (nodata, banddata))
        result_ds.GetRasterBand(band + 1).WriteArray(banddata)
    return 1


def check_vector_prj(shp_dataset, raster_srs):
    # 获取图层
    shp_lyr = shp_dataset.GetLayer(0)
    shp_sr = shp_lyr.GetSpatialRef()
    # 矢量栅格化
    # 判断两个SRS的基准是否一致
    if not shp_sr.IsSameGeogCS(raster_srs):
        sys.exit("两个空间参考的基准面不一致，不能进行投影转换！！！")
    # 判断两个SRS是否一致
    elif shp_sr.IsSame(raster_srs):
        rpj_shp_l = shp_lyr
        rpj_shp_ds = shp_dataset
        shp_lyr = None
        shp_dataset = None
    else:
        rpj_shp_ds, rpj_shp_l = rpj_vec(shp_lyr, raster_srs)
    return rpj_shp_ds, rpj_shp_l


def create_mask(raster_ds, ext):
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
    mask_ds = gdal.GetDriverByName('MEM').Create('', int(x_size), int(y_size), 1, gdal.GDT_Byte)
    mask_ds.SetProjection(raster_prj)
    mask_geo = [ulx, raster_geo[1], 0, uly, 0, raster_geo[5]]
    mask_ds.SetGeoTransform(mask_geo)
    return mask_ds


def main(file, in_sampe_shp, in_boundry_shp, out_mask, out_image):
    # 打开栅格
    raster_ds = gdal.Open(file)
    raster_geo = raster_ds.GetGeoTransform()
    raster_srs_wkt = raster_ds.GetProjection()
    raster_srs = osr.SpatialReference()
    raster_srs.ImportFromWkt(raster_srs_wkt)
    # 打开矩形范围矢量
    boundary_shp_ds = ogr.Open(in_boundry_shp)
    # 检查矢量是否和栅格的投影一致，如不一致重投影
    re_boundary_shp_ds, re_boundary_shp_l = check_vector_prj(boundary_shp_ds, raster_srs)
    # 依据矩形范围创建掩模
    # 计算矢量和栅格的最小重叠矩形
    boundary_offset = min_rect(raster_ds, re_boundary_shp_l)
    # 判断是否有重叠区域，如无（0），则跳过
    if boundary_offset == 0:
        sys.exit("Vector and raster has no overlap area")
    # 矢量栅格化
    mask_ds = create_mask(raster_ds, boundary_offset)
    # 处理mask
    re_boundary_shp_ds = None
    sample_shp_ds = ogr.Open(in_sampe_shp)
    # 检查矢量是否和栅格的投影一致，如不一致重投影
    re_sample_shp_ds, re_sample_shp_l = check_vector_prj(sample_shp_ds, raster_srs)
    for feat in re_sample_shp_l:
        # 要素提取为图层
        feat_ds, feat_lyr = Feature_memory_shp(feat, raster_srs)
        # 要素裁剪
        # 计算矢量和掩模的最小重叠矩形
        offset = min_rect(mask_ds, feat_lyr)
        # 判断是否有重叠区域，如无（0），则跳过
        if offset == 0:
            continue
        # 获取重叠区域数组
        # 将行列整数浮点化
        offset = np.array(offset) * 1.0
        # 根据最小重叠矩形的范围进行矢量栅格化
        # ulx, uly = gdal.ApplyGeoTransform(raster_geo, offset[0], offset[1])
        x_size = offset[2] - offset[0]
        y_size = offset[3] - offset[1]
        overlap = mask_ds.GetRasterBand(1).ReadAsArray(int(offset[0]), int(offset[1]), int(x_size), int(y_size))
        # 矢量栅格化
        sample_mask_ds = shp2raster(mask_ds, feat_lyr, offset)
        # 获取掩模数据
        sample_mask_array = sample_mask_ds.ReadAsArray()
        real_overlap = np.choose(sample_mask_array, (overlap, 1))
        mask_ds.GetRasterBand(1).WriteArray(real_overlap, int(offset[0]), int(offset[1]))
        feat_ds = None
    # 利用创建好的mask进行影像裁剪
    # 进行裁剪
    res = mask_raster(raster_ds, mask_ds, out_image, boundary_offset)
    # 输出mask
    tif_driver = gdal.GetDriverByName('GTiff')
    out_res = tif_driver.CreateCopy(out_mask, mask_ds, strict=1, callback=progress)
    mask_ds = None
    raster_ds = None
    return None


if __name__ == '__main__':
    # 支持中文路径
    gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
    # 支持中文属性字段sample
    gdal.SetConfigOption("SHAPE_ENCODING", "GBK")
    # 注册所有ogr驱动
    ogr.RegisterAll()
    # 注册所有gdal驱动
    gdal.AllRegister()
    start_time = time.clock()
    in_file = r"F:\test_data\unet_test\少帅需求数据\GF2_20190703_L1A0004100556_zhiyanqu.tif"
    in_sampe_shp = r"F:\test_data\unet_test\少帅需求数据\yancao_L1A0004100556_1.shp"
    in_boundry_shp = r"F:\test_data\unet_test\少帅需求数据\sample_L1A0004100556_1.shp"
    out_mask = r"F:\test_data\unet_test\少帅需求数据\GF2_20190703_L1A0004100556_zhiyanqu_mask.tif"
    out_image = r"F:\test_data\unet_test\少帅需求数据\GF2_20190703_L1A0004100556_zhiyanqu_sample.tif"
    main(in_file, in_sampe_shp, in_boundry_shp, out_mask, out_image)
    end_time = time.clock()
    print("time: %.4f secs." % (end_time - start_time))
