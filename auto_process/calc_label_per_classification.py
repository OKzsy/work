#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2020/8/6 10:34
# @Author  : zhaoss
# @FileName: calc_label_per_classification.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import sys
import glob
import time
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress

gdal.UseExceptions()


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
    mem_ds.SyncToDisk()
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
    mask_ds = gdal.GetDriverByName('MEM').Create('', int(x_size), int(y_size), 1, gdal.GDT_UInt16)
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
        return 0
    # 限定重叠范围在栅格影像上
    # 列
    offset_column = np.array([off_ulx, off_drx])
    offset_column = np.maximum((np.minimum(offset_column, x_size - 1)), 0)
    # 行
    offset_line = np.array([off_uly, off_dry])
    offset_line = np.maximum((np.minimum(offset_line, y_size - 1)), 0)
    # 强制矢量对应最小行列为1个像元
    if offset_line[1] == offset_line[0]:
        offset_line[1] += 1
    if offset_column[1] == offset_column[0]:
        offset_column[1] += 1
    return [offset_column[0], offset_line[0], offset_column[1], offset_line[1]]


def main(file, shp, flags, out):
    # 打开栅格
    raster_ds = gdal.Open(file)
    raster_geo = raster_ds.GetGeoTransform()
    raster_srs_wkt = raster_ds.GetProjection()
    raster_srs = osr.SpatialReference()
    raster_srs.ImportFromWkt(raster_srs_wkt)
    # 打开矢量
    shp_ds = ogr.Open(shp)
    # 获取图层
    shp_lyr = shp_ds.GetLayer(0)
    shp_sr = shp_lyr.GetSpatialRef()
    # 矢量栅格化
    # 判断两个SRS的基准是否一致
    if not shp_sr.IsSameGeogCS(raster_srs):
        sys.exit("两个空间参考的基准面不一致，不能进行投影转换！！！")
    # 判断两个SRS是否一致
    elif shp_sr.IsSame(raster_srs):
        re_shp_l = shp_lyr
        re_shp_ds = shp_ds
        shp_lyr = None
    else:
        re_shp_ds, re_shp_l = rpj_vec(shp_lyr, raster_srs)
    # 拆分矢量用以对单个要素进行裁剪
    driver = gdal.GetDriverByName('MEM')
    mem_ds = driver.CreateCopy("", raster_ds, strict=1)
    # 定义变量用以显示进度条
    count = 0
    num_feature = re_shp_l.GetFeatureCount()
    # 创建结果shp
    shp_driver = ogr.GetDriverByName('ESRI Shapefile')
    out_shp_ds = shp_driver.CreateDataSource(out)
    out_lyr = out_shp_ds.CreateLayer(' ', geom_type=re_shp_l.GetGeomType(), srs=raster_srs)
    # 为结果shp添加原字段信息
    # out_lyr.CreateFields(re_shp_l.schema)
    # 为结果shp添加新字段信息
    coord_fld = ogr.FieldDefn('percent', ogr.OFTReal)
    coord_fld.SetWidth(8)
    coord_fld.SetPrecision(3)
    coord_fld.SetDefault('0')
    out_lyr.CreateField(coord_fld)
    # 创建虚拟要素用以输出
    out_defn = out_lyr.GetLayerDefn()
    out_feat = ogr.Feature(out_defn)
    for feat in re_shp_l:
        progress((count + 1) / num_feature)
        count += 1
        # 要素提取为图层
        feat_ds, feat_lyr = Feature_memory_shp(feat, raster_srs)
        # 要素裁剪
        # 计算矢量和栅格的最小重叠矩形
        offset = min_rect(raster_ds, feat_lyr)
        # 判断是否有重叠区域，如无（0），则跳过
        if offset == 0:
            continue
        # 获取重叠区域数组
        # 将行列整数浮点化
        offset = np.array(offset) * 1.0
        # 根据最小重叠矩形的范围进行矢量栅格化
        x_size = offset[2] - offset[0]
        y_size = offset[3] - offset[1]
        overlap = mem_ds.GetRasterBand(1).ReadAsArray(int(offset[0]), int(offset[1]), int(x_size), int(y_size))
        # 矢量栅格化
        mask_ds = shp2raster(raster_ds, feat_lyr, offset)
        # 获取掩模数据
        mask_array = mask_ds.ReadAsArray()
        real_overlap = np.choose(mask_array, (np.nan, overlap))
        # 统计指定标签所占的比例
        # 统计非背景值像元个数
        real_value_count = real_overlap.size - np.where(np.isnan(real_overlap))[0].shape[0]
        flags_pre = []
        for iflag in flags:
            flag_num = np.where(real_overlap == iflag)[0].shape[0]
            if real_value_count == 0:
                flag_pre = 0
            else:
                flag_pre = flag_num / real_value_count
            flags_pre.append(flag_pre)
        real_overlap = None
        max_pre = max(flags_pre)
        if max_pre == 0:
            continue
        out_feat.SetGeometry(feat.geometry().Clone())
        out_feat.SetField('percent', max_pre)
        out_lyr.CreateFeature(out_feat)
        mask_ds = None
        feat_ds = None
    out_shp_ds.SyncToDisk()
    out_shp_ds = None
    re_shp_l = None
    mem_ds = None
    raster_ds = None
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
    in_file = r"\\192.168.0.234\nydsj\user\ZSS\2020yancao\S2\平顶山3镇\class\L2A_T49SFT_20200810_平顶山3镇_class.tif"
    in_shp = r"\\192.168.0.234\nydsj\user\ZSS\2020yancao\S2\平顶山3镇\DK\dk_pds_wgs84.shp"
    outpath = r"\\192.168.0.234\nydsj\user\ZSS\2020yancao\S2\平顶山3镇\DK_res\pingdingshan.shp"
    category_flags = [0]
    main(in_file, in_shp, category_flags, outpath)

    end_time = time.time()

    print("time: %.4f secs." % (end_time - start_time))

