#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Author:zhaoss
Email:zhaoshaoshuai@hnnydsj.com
Create date: 2019/2/10 15:01
File: pan.py
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
    # out = r"F:\test_data\mask.tif"
    # mask_ds = gdal.GetDriverByName('GTiff').Create(out, int(x_size), int(y_size), 1, gdal.GDT_Byte)
    mask_ds = gdal.GetDriverByName('MEM').Create('', int(x_size), int(y_size), 1, gdal.GDT_Byte)
    mask_ds.SetProjection(raster_prj)
    mask_geo = [ulx, raster_geo[1], 0, uly, 0, raster_geo[5]]
    mask_ds.SetGeoTransform(mask_geo)
    # 矢量栅格化
    print('Begin shape to mask')
    gdal.RasterizeLayer(mask_ds, [1], shp_layer, burn_values=[1], callback=progress)
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
        sys.exit("Have no overlap")
    # 限定重叠范围在栅格影像上
    # 列
    offset_column = np.array([off_ulx, off_drx])
    offset_column = np.maximum((np.minimum(offset_column, x_size - 1)), 0)
    # 行
    offset_line = np.array([off_uly, off_dry])
    offset_line = np.maximum((np.minimum(offset_line, y_size - 1)), 0)

    return [offset_column[0], offset_line[0], offset_column[1], offset_line[1]]


def subsat(raster_ds=None, mask_ds=None, result_ds=None, block_size=100):
    xsize = raster_ds.RasterXSize
    ysize = raster_ds.RasterYSize
    block_size = block_size
    bandcount = raster_ds.RasterCount
    print("Begin deal with subsat!")
    for band in range(bandcount):
        for y in range(0, ysize, block_size):
            if y + block_size < ysize:
                rows = block_size
            else:
                rows = ysize - y
            cols = xsize
            raster_data = raster_ds.GetRasterBand(band + 1).ReadAsArray(0, y, cols, rows)
            mask_data = mask_ds.GetRasterBand(1).ReadAsArray(0, y, cols, rows)
            mask_data = 1 - mask_data
            banddata = np.choose(mask_data, (raster_data, 0))
            result_ds.GetRasterBand(band + 1).WriteArray(banddata, 0, y)
            progress(y / ysize)
    progress(1.1)
    return result_ds


def mask_raster(raster_ds, mask_ds, outfile, ext, nodata):
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
    print('Begin mask')
    progress(0.0)
    for band in range(bandCount):
        banddata = raster_ds.GetRasterBand(band + 1).ReadAsArray(int(ext[0]), int(ext[1]), int(x_size), int(y_size))
        banddata = np.choose(mask, (banddata, nodata))
        if nodata is not None:
            result_ds.GetRasterBand(band + 1).SetNoDataValue(nodata)
        result_ds.GetRasterBand(band + 1).WriteArray(banddata)
        progress((1 + band) / bandCount)
    # tmp = subsat(raster_ds, mask_ds, result_ds, block_size=500)
    return 1


def main(raster, shp, out, nodata=None):
    # 打开栅格和矢量影像
    raster_ds = gdal.Open(raster)
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
    # 计算矢量和栅格的最小重叠矩形
    offset = min_rect(raster_ds, re_shp_l)
    # 矢量栅格化
    mask_ds = shp2raster(raster_ds, re_shp_l, offset)
    # 进行裁剪
    res = mask_raster(raster_ds, mask_ds, out, offset, nodata)

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
    in_file = r"\\192.168.0.234\nydsj\user\ZSS\农保项目\遥感院提供img\2.atm\GF1C_PMS_E112.7_N34.1_20190824_L1A1021462411-PAN_atm.tif"
    shpfile = r"\\192.168.0.234\nydsj\user\ZSS\农保项目\shp\20190816\GF1C_PMS_E112.7_N34.1_20190824_L1A1021462411.shp"
    outfile = r"\\192.168.0.234\nydsj\user\ZSS\农保项目\遥感院提供img\2.atm\20190816_ruzhou\GF1C_PMS_E112.7_N34.1_20190824_L1A1021462411-PAN_atm.tif"
    # nodata = 200
    print('The program starts running!')
    # in_file = sys.argv[1]
    # shpfile = sys.argv[2]
    # outfile = sys.argv[3]
    # nodata = sys.argv[4]

    main(in_file, shpfile, outfile)

    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
