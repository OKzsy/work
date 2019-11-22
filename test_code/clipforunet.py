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
    x_size = ext[2] - ext[0]
    y_size = ext[3] - ext[1]
    mask_ds = gdal.GetDriverByName('MEM').Create('', int(x_size), int(y_size), 1, gdal.GDT_Byte)
    mask_ds.SetProjection(raster_prj)
    mask_geo = [ulx, raster_geo[1], 0, uly, 0, raster_geo[5]]
    mask_ds.SetGeoTransform(mask_geo)
    gdal.RasterizeLayer(mask_ds, [1], shp_layer, burn_values=[1])
    return mask_ds


def Feature_memory_shp(feat, sr):
    """将指定的geometry导出为内存中单独的shpfile"""
    fid = feat.GetFID()
    mem_dri = ogr.GetDriverByName('Memory')
    mem_ds = mem_dri.CreateDataSource(' ')
    outLayer = mem_ds.CreateLayer(' ', geom_type=ogr.wkbPolygon, srs=sr)
    coor_fld = ogr.FieldDefn('ID_FID', ogr.OFTInteger)
    outLayer.CreateField(coor_fld)
    out_defn = outLayer.GetLayerDefn()
    out_feat = ogr.Feature(out_defn)
    fld_index = outLayer.GetLayerDefn().GetFieldIndex('ID_FID')
    out_feat.SetField(fld_index, fid)
    out_feat.SetGeometry(feat.geometry())
    outLayer.CreateFeature(out_feat)
    return mem_ds, outLayer


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

    return [offset_column[0], offset_line[0], offset_column[1], offset_line[1]]


def mask_raster(raster_ds, mask_ds, outfile, ext):
    ext = np.array(ext) * 1.0
    raster_prj = raster_ds.GetProjection()
    raster_geo = raster_ds.GetGeoTransform()
    bandCount = raster_ds.RasterCount
    dataType = raster_ds.GetRasterBand(1).DataType
    ulx, uly = gdal.ApplyGeoTransform(raster_geo, ext[0], ext[1])
    x_size = ext[2] - ext[0]
    y_size = ext[3] - ext[1]
    result_ds = gdal.GetDriverByName('GTiff').Create(outfile, int(x_size), int(y_size), bandCount, dataType)
    result_ds.SetProjection(raster_prj)
    result_geo = [ulx, raster_geo[1], 0, uly, 0, raster_geo[5]]
    result_ds.SetGeoTransform(result_geo)
    mask = mask_ds.GetRasterBand(1).ReadAsArray()
    nodata = 0
    for band in range(bandCount):
        banddata = raster_ds.GetRasterBand(band + 1).ReadAsArray(int(ext[0]), int(ext[1]), int(x_size), int(y_size))
        banddata = np.choose(mask, (nodata, banddata))
        result_ds.GetRasterBand(band + 1).WriteArray(banddata)
    return 1


def check_vector_prj(shp_dataset, raster_srs):
    shp_lyr = shp_dataset.GetLayer(0)
    shp_sr = shp_lyr.GetSpatialRef()
    if not shp_sr.IsSameGeogCS(raster_srs):
        sys.exit("两个空间参考的基准面不一致，不能进行投影转换！！！")
    elif shp_sr.IsSame(raster_srs):
        rpj_shp_l = shp_lyr
        rpj_shp_ds = shp_dataset
        shp_lyr = None
        shp_dataset = None
    else:
        rpj_shp_ds, rpj_shp_l = rpj_vec(shp_lyr, raster_srs)
    return rpj_shp_ds, rpj_shp_l


def create_mask(raster_ds, ext):
    ext = np.array(ext) * 1.0
    raster_prj = raster_ds.GetProjection()
    raster_geo = raster_ds.GetGeoTransform()
    ulx, uly = gdal.ApplyGeoTransform(raster_geo, ext[0], ext[1])
    x_size = ext[2] - ext[0]
    y_size = ext[3] - ext[1]
    mask_ds = gdal.GetDriverByName('MEM').Create('', int(x_size), int(y_size), 1, gdal.GDT_Byte)
    mask_ds.SetProjection(raster_prj)
    mask_geo = [ulx, raster_geo[1], 0, uly, 0, raster_geo[5]]
    mask_ds.SetGeoTransform(mask_geo)
    return mask_ds


def main(file, in_sampe_shp, in_boundry_shp, out_mask, out_image):
    raster_ds = gdal.Open(file)
    raster_geo = raster_ds.GetGeoTransform()
    raster_srs_wkt = raster_ds.GetProjection()
    raster_srs = osr.SpatialReference()
    raster_srs.ImportFromWkt(raster_srs_wkt)
    boundary_shp_ds = ogr.Open(in_boundry_shp)
    re_boundary_shp_ds, re_boundary_shp_l = check_vector_prj(boundary_shp_ds, raster_srs)
    boundary_offset = min_rect(raster_ds, re_boundary_shp_l)
    if boundary_offset == 0:
        sys.exit("Vector and raster has no overlap area")
    mask_ds = create_mask(raster_ds, boundary_offset)
    re_boundary_shp_ds = None
    sample_shp_ds = ogr.Open(in_sampe_shp)
    re_sample_shp_ds, re_sample_shp_l = check_vector_prj(sample_shp_ds, raster_srs)
    for feat in re_sample_shp_l:
        feat_ds, feat_lyr = Feature_memory_shp(feat, raster_srs)
        offset = min_rect(mask_ds, feat_lyr)
        if offset == 0:
            continue
        offset = np.array(offset) * 1.0
        x_size = offset[2] - offset[0]
        y_size = offset[3] - offset[1]
        overlap = mask_ds.GetRasterBand(1).ReadAsArray(int(offset[0]), int(offset[1]), int(x_size), int(y_size))
        sample_mask_ds = shp2raster(mask_ds, feat_lyr, offset)
        sample_mask_array = sample_mask_ds.ReadAsArray()
        real_overlap = np.choose(sample_mask_array, (overlap, 1))
        mask_ds.GetRasterBand(1).WriteArray(real_overlap, int(offset[0]), int(offset[1]))
        feat_ds = None
    res = mask_raster(raster_ds, mask_ds, out_image, boundary_offset)
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
