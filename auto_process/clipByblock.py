#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/7/15 15:38
# @Author  : zhaoss
# @FileName: clipByblock.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
对输入影像进行指定范围裁剪

Parameters


"""

import os
import glob
import time
import sys
import math
import fnmatch
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress

def searchfiles(dirpath, partfileinfo='*', recursive=False):
    """列出符合条件的文件(包含路径), 默认不进行递归查询, 当recursive为True时同时查询子文件夹"""
    # 定义结果输出列表
    filelist = []
    # 列出根目录下包含文件夹在内的所有文件目录
    pathlist = glob.glob(os.path.join(os.path.sep, dirpath, "*"))
    # 逐文件进行判断
    for mpath in pathlist:
        if os.path.isdir(mpath):
            # 默认不判断子文件夹
            if recursive:
                filelist += searchfiles(mpath, partfileinfo, recursive)
        elif fnmatch.fnmatch(os.path.basename(mpath), partfileinfo):
            filelist.append(mpath)
        # 如果mpath为子文件夹，则进行递归调用，判断子文件夹下的文件

    return filelist


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
    x_size = ext[2]
    y_size = ext[3]
    # 创建mask
    # out = r"F:\test_data\mask.tif"
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
        sys.exit("Have no overlap")
    # 限定重叠范围在栅格影像上
    # 列
    offset_column = np.array([off_ulx, off_drx])
    offset_column = np.maximum((np.minimum(offset_column, x_size - 1)), 0)
    # 行
    offset_line = np.array([off_uly, off_dry])
    offset_line = np.maximum((np.minimum(offset_line, y_size - 1)), 0)
    # 总行列数
    colums = offset_column[1] - offset_column[0] + 1
    rows = offset_line[1] - offset_line[0] + 1
    return [x * 1.0 for x in [offset_column[0], offset_line[0], colums, rows]]


def mask_raster(raster_ds, mask_ds, result_ds, ext, nodata):
    if nodata == None:
        background = 0
    else:
        background = nodata
    # 将行列整数浮点化
    ext = np.array(ext) * 1.0
    # 获取栅格数据的基本信息
    raster_geo = raster_ds.GetGeoTransform()
    bandCount = raster_ds.RasterCount
    dataType = raster_ds.GetRasterBand(1).DataType
    # 根据最小重叠矩形的范围进行矢量栅格化
    x_size = ext[2]
    y_size = ext[3]
    # 获取掩模
    mask = mask_ds.GetRasterBand(1).ReadAsArray()
    # 对原始影像进行掩模并输出
    for band in range(bandCount):
        banddata = raster_ds.GetRasterBand(band + 1).ReadAsArray(int(ext[0]), int(ext[1]), int(x_size), int(y_size))
        banddata = np.choose(mask, (background, banddata))
        result_ds.GetRasterBand(band + 1).WriteArray(banddata, 0, int(ext[1] - ext[4]))
    result_ds.FlushCache()
    return 1


def Corner_coordinates(dataset):
    # 获取原始影像的放射变换参数
    geo_t = dataset.GetGeoTransform()
    x_size = dataset.RasterXSize
    y_size = dataset.RasterYSize
    # 获取影像的四个角点地理坐标
    # 左上
    old_ulx, old_uly = gdal.ApplyGeoTransform(geo_t, 0, 0)
    # 右上
    old_urx, old_ury = gdal.ApplyGeoTransform(geo_t, x_size, 0)
    # 左下
    old_dlx, old_dly = gdal.ApplyGeoTransform(geo_t, 0, y_size)
    # 右下
    old_drx, old_dry = gdal.ApplyGeoTransform(geo_t, x_size, y_size)

    return [old_ulx, old_uly, old_drx, old_dry]


def main(file, shp, out_dir, nodata=None):
    # 判断输入的是否为文件
    if os.path.isdir(file):
        rasters = searchfiles(file, partfileinfo='*.tif')
    else:
        rasters = [file]
    # 打开矢量文件
    shp_ds = ogr.Open(shp)
    shp_lyr = shp_ds.GetLayer()
    shp_sr = shp_lyr.GetSpatialRef()
    # 打开栅格和矢量影像
    for raster in rasters:
        basename = os.path.basename(raster)
        raster_ds = gdal.Open(raster)
        raster_prj = raster_ds.GetProjection()
        raster_geo = raster_ds.GetGeoTransform()
        bandCount = raster_ds.RasterCount
        dataType = raster_ds.GetRasterBand(1).DataType
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
            re_shp_ds = shp_ds
            
        else:
            re_shp_ds, re_shp_l = rpj_vec(shp_lyr, raster_srs)
        # 获取影像的左上右下点交点坐标
        corner = Corner_coordinates(raster_ds)
        # 对原始图层进行空间过滤
        re_shp_l.SetSpatialFilterRect(corner[0], corner[3], corner[2], corner[1])
        # 复制经过属性过滤的图层
        mem_dri = ogr.GetDriverByName('Memory')
        temp_shp_ds = mem_dri.CreateDataSource(' ')
        new_shp_l = temp_shp_ds.CopyLayer(re_shp_l, 'new_shp_l')
        # 计算矢量和栅格的最小重叠矩形
        offset = min_rect(raster_ds, new_shp_l)
        # 创建输出影像
        out = os.path.join(out_dir, basename)
        ulx, uly = gdal.ApplyGeoTransform(raster_geo, offset[0], offset[1])
        result_ds = gdal.GetDriverByName('GTiff').Create(out, int(offset[2]), int(offset[3]), bandCount, dataType)
        result_ds.SetProjection(raster_prj)
        result_geo = [ulx, raster_geo[1], 0, uly, 0, raster_geo[5]]
        result_ds.SetGeoTransform(result_geo)
        # 嫁接分块裁切
        ysize = int(offset[3]) + int(offset[1])
        xsize = int(offset[2])
        block_size = 300
        count = 1
        total_block = max(int(int(offset[3]) / block_size), 1)
        for y in range(int(offset[1]), ysize, block_size):
            if y + block_size < ysize:
                rows = block_size
            else:
                rows = ysize - y
            cols = xsize
            extent = [offset[0], y, cols, rows, offset[1]]
            # 分块矢量栅格化
            mask_ds = shp2raster(raster_ds, new_shp_l, extent)
            # 分块裁切
            res = mask_raster(raster_ds, mask_ds, result_ds, extent, nodata)
            mask_ds = None
            progress(count / total_block)
            count += 1
        # progress(1.0)

        temp_shp_ds = None
        new_shp_l = None
        re_shp_ds = None
        raster_ds = None
    shp_ds = None
    shp_lyr = None
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
    in_file = r"F:\test\chanliang\clip\ttvi"
    shpfile = r"F:\test\chanliang\2022小麦实际播种_公司种_终.shp"
    outfile = r"F:\test\chanliang\clip\clip\ttvi"
    nodata = 0

    print('The program starts running!')

    main(in_file, shpfile, outfile, nodata)

    end_time = time.time()

    print("time: %.4f secs." % (end_time - start_time))
