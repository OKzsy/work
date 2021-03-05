#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2021/1/12 16:53
# @Author  : zhaoss
# @FileName: statisticByfield.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
根据输入地块边界和分级标准进行相关参数统计

Parameters


"""

import sys, getopt
import time
import numpy as np
from osgeo import gdal, ogr

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def mask_raster(raster_ds, mask_ds, ext):
    # 将行列整数浮点化
    ext = np.array(ext) * 1.0
    # 获取栅格数据的基本信息
    bandCount = raster_ds.RasterCount
    # 根据最小重叠矩形的范围进行矢量栅格化
    x_size = ext[2] - ext[0]
    y_size = ext[3] - ext[1]
    # 获取掩模
    mask = mask_ds.GetRasterBand(1).ReadAsArray()
    mask = 1 - mask
    # 对原始影像进行掩模并输出
    for band in range(bandCount):
        banddata = raster_ds.GetRasterBand(
            band + 1).ReadAsArray(int(ext[0]), int(ext[1]), int(x_size), int(y_size))
        banddata = np.choose(mask, (banddata, 0))
    return banddata


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
    mask_ds = gdal.GetDriverByName('MEM').Create(
        '', int(x_size), int(y_size), 1, gdal.GDT_Byte)
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
    off_ulx, off_uly = map(round, gdal.ApplyGeoTransform(
        raster_inv_geo, extent[0], extent[3]))
    # 右下
    off_drx, off_dry = map(round, gdal.ApplyGeoTransform(
        raster_inv_geo, extent[1], extent[2]))
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


def main(geo_json, color, src):
    # geojson转矢量
    poly_from_geojson = ogr.CreateGeometryFromJson(geo_json)
    osrs = poly_from_geojson.GetSpatialReference()
    mem_drive = ogr.GetDriverByName('Memory')
    mem_ds = mem_drive.CreateDataSource('')
    mem_lyr = mem_ds.CreateLayer('', srs=osrs, geom_type=ogr.wkbPolygon)
    fld = ogr.FieldDefn('tag_id', ogr.OFTString)
    mem_lyr.CreateField(fld)
    out_defn = mem_lyr.GetLayerDefn()
    out_feat = ogr.Feature(out_defn)
    out_feat.SetGeometry(poly_from_geojson)
    mem_lyr.CreateFeature(out_feat)
    # 裁剪
    # 打开栅格影星
    raster_ds = gdal.Open(src)
    # 计算矢量和栅格的最小重叠矩形
    offset = min_rect(raster_ds, mem_lyr)
    # 判断是否有重叠区域，如无（0），则跳过
    if offset == 0:
        sys.exit("The geometry entered exceeds the boundary")
    # 矢量栅格化
    mask_ds = shp2raster(raster_ds, mem_lyr, offset)
    # 进行裁剪
    field_data = mask_raster(raster_ds, mask_ds, offset)
    # 统计
    # 获取颜色表
    col_talbe = np.loadtxt(color, dtype=np.float, delimiter=',')
    # 获取影像中不为0像元的总个数和位置索引
    nozero_index = np.where(field_data != 0)
    nozero_count = nozero_index[0].shape[0]
    valid_value = field_data[nozero_index]
    fb = open(color, 'w', newline='')
    for iline in col_talbe:
        slice_min = iline[1]
        slice_max = iline[2]
        slice_index = np.where((valid_value >= slice_min) & (valid_value < slice_max))
        percent = slice_index[0].shape[0] / nozero_count
        line = ','.join([str(int(iline[0])), str(iline[1]), str(iline[2]), str(int(iline[3])), str(int(iline[4])),
                         str(int(iline[5])), str(round(percent, 3))]) + '\n'
        fb.write(line)
    fb.close
    mem_ds.Destroy()
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
    argv = sys.argv[1:]
    try:
        opts, args = getopt.getopt(argv, "hj:c:s:", ["geo_json=", "color_table=", "src_file="])
    except getopt.GetoptError:
        print('statisticByfield.py -j <geo_json> -c <color_table> -s <src_file>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print("""
            statisticByfield.py -j|--geo_json= 'geometry GeoJson'
            -c|--color_table= 'The path of color table'
            -s|--src_file= 'The path of image file'
            """)
            sys.exit()
        elif opt in ("-j", "--geo_json"):
            geo_json = arg
        elif opt in ("-c", "--color_table"):
            color_table = arg
        elif opt in ("-s", "--src_file"):
            src_file = arg
    main(geo_json, color_table, src_file)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
