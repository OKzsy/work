#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/7/15 15:38
# @Author  : zhaoss
# @FileName: clipByblock.py
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
    mem_dri = ogr.GetDriverByName('Memory')
    mem_ds = mem_dri.CreateDataSource(' ')
    outLayer = mem_ds.CreateLayer(' ', geom_type=lyr.GetGeomType(), srs=srs)
    outLayer.CreateFields(lyr.schema)
    out_feat = ogr.Feature(outLayer.GetLayerDefn())
    for in_feat in lyr:
        geom = in_feat.geometry().Clone()
        geom.TransformTo(srs)
        out_feat.SetGeometry(geom)
        for i in range(in_feat.GetFieldCount()):
            out_feat.SetField(i, in_feat.GetField(i))
        outLayer.CreateFeature(out_feat)
    return mem_ds, outLayer


def shp2raster(raster_ds, shp_layer, ext):
    ext = np.array(ext) * 1.0
    raster_prj = raster_ds.GetProjection()
    raster_geo = raster_ds.GetGeoTransform()
    ulx, uly = gdal.ApplyGeoTransform(raster_geo, ext[0], ext[1])
    x_size = ext[2]
    y_size = ext[3]
    mask_ds = gdal.GetDriverByName('MEM').Create('', int(x_size), int(y_size), 1, gdal.GDT_Byte)
    mask_ds.SetProjection(raster_prj)
    mask_geo = [ulx, raster_geo[1], 0, uly, 0, raster_geo[5]]
    mask_ds.SetGeoTransform(mask_geo)
    gdal.RasterizeLayer(mask_ds, [1], shp_layer, burn_values=[1])
    return mask_ds


def min_rect(raster_ds, shp_layer):
    x_size = raster_ds.RasterXSize
    y_size = raster_ds.RasterYSize
    extent = shp_layer.GetExtent()
    raster_geo = raster_ds.GetGeoTransform()
    raster_inv_geo = gdal.InvGeoTransform(raster_geo)
    off_ulx, off_uly = map(round, gdal.ApplyGeoTransform(raster_inv_geo, extent[0], extent[3]))
    off_drx, off_dry = map(round, gdal.ApplyGeoTransform(raster_inv_geo, extent[1], extent[2]))
    if off_ulx >= x_size or off_uly >= y_size or off_drx <= 0 or off_dry <= 0:
        sys.exit("Have no overlap")
    offset_column = np.array([off_ulx, off_drx])
    offset_column = np.maximum((np.minimum(offset_column, x_size - 1)), 0)
    offset_line = np.array([off_uly, off_dry])
    offset_line = np.maximum((np.minimum(offset_line, y_size - 1)), 0)
    colums = offset_column[1] - offset_column[0] + 1
    rows = offset_line[1] - offset_line[0] + 1
    return [x * 1.0 for x in [offset_column[0], offset_line[0], colums, rows]]


def mask_raster(raster_ds, mask_ds, result_ds, ext, nodata):
    if nodata == None:
        background = 0
    else:
        background = nodata
    ext = np.array(ext) * 1.0
    raster_geo = raster_ds.GetGeoTransform()
    bandCount = raster_ds.RasterCount
    dataType = raster_ds.GetRasterBand(1).DataType
    x_size = ext[2]
    y_size = ext[3]
    mask = mask_ds.GetRasterBand(1).ReadAsArray()
    for band in range(bandCount):
        banddata = raster_ds.GetRasterBand(band + 1).ReadAsArray(int(ext[0]), int(ext[1]), int(x_size), int(y_size))
        banddata = np.choose(mask, (background, banddata))
        result_ds.GetRasterBand(band + 1).WriteArray(banddata, 0, int(ext[1] - ext[4]))
    result_ds.FlushCache()
    return 1


def Corner_coordinates(dataset):
    geo_t = dataset.GetGeoTransform()
    x_size = dataset.RasterXSize
    y_size = dataset.RasterYSize
    old_ulx, old_uly = gdal.ApplyGeoTransform(geo_t, 0, 0)
    old_urx, old_ury = gdal.ApplyGeoTransform(geo_t, x_size, 0)
    old_dlx, old_dly = gdal.ApplyGeoTransform(geo_t, 0, y_size)
    old_drx, old_dry = gdal.ApplyGeoTransform(geo_t, x_size, y_size)

    return [old_ulx, old_uly, old_drx, old_dry]


def main(raster, shp, out, nodata=None):
    raster_ds = gdal.Open(raster)
    raster_prj = raster_ds.GetProjection()
    raster_geo = raster_ds.GetGeoTransform()
    bandCount = raster_ds.RasterCount
    dataType = raster_ds.GetRasterBand(1).DataType
    shp_ds = ogr.Open(shp)
    shp_lyr = shp_ds.GetLayer()
    shp_sr = shp_lyr.GetSpatialRef()
    raster_srs_wkt = raster_ds.GetProjection()
    raster_srs = osr.SpatialReference()
    raster_srs.ImportFromWkt(raster_srs_wkt)
    if not shp_sr.IsSameGeogCS(raster_srs):
        sys.exit("两个空间参考的基准面不一致，不能进行投影转换！！！")
    elif shp_sr.IsSame(raster_srs):
        re_shp_l = shp_lyr
        shp_lyr = None
    else:
        re_shp_ds, re_shp_l = rpj_vec(shp_lyr, raster_srs)
    corner = Corner_coordinates(raster_ds)
    re_shp_l.SetSpatialFilterRect(corner[0], corner[1], corner[2], corner[3])
    offset = min_rect(raster_ds, re_shp_l)
    ulx, uly = gdal.ApplyGeoTransform(raster_geo, offset[0], offset[1])
    result_ds = gdal.GetDriverByName('GTiff').Create(out, int(offset[2]), int(offset[3]), bandCount, dataType)
    result_ds.SetProjection(raster_prj)
    result_geo = [ulx, raster_geo[1], 0, uly, 0, raster_geo[5]]
    result_ds.SetGeoTransform(result_geo)
    ysize = int(offset[3]) + int(offset[1])
    xsize = int(offset[2])
    block_size = 300
    count = 1
    total_block = int(int(offset[3]) / block_size)
    for y in range(int(offset[1]), ysize, block_size):
        if y + block_size < ysize:
            rows = block_size
        else:
            rows = ysize - y
        cols = xsize
        extent = [offset[0], y, cols, rows, offset[1]]
        mask_ds = shp2raster(raster_ds, re_shp_l, extent)
        res = mask_raster(raster_ds, mask_ds, result_ds, extent, nodata)
        mask_ds = None
        progress(count / total_block)
        count += 1
    progress(1.0)
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
    in_file = r"\\192.168.0.234\nydsj\project\2.zhiyan\2.2019\2.data\3.GF_yancao\4.clip\GF1B_20190602_L1A1227642138_zhiyanqu.tif"
    shpfile = r"\\192.168.0.234\nydsj\project\2.zhiyan\2.2019\1.vector\1.xzqh\故县镇.shp"
    outfile = r"\\192.168.0.234\nydsj\project\2.zhiyan\2.2019\2.data\3.GF_yancao\4.clip\GF1B_20190602_L1A1227642138_故县镇.tif"
    nodata = None
    print('The program starts running!')

    main(in_file, shpfile, outfile, nodata)

    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
