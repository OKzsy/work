#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/3/12 14:59
# @Author  : zhaoss
# @FileName: multi_improveWheatClass.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import sys
import glob
import time
import fnmatch
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
            banddata = np.choose(mask_data, (raster_data, 0))
            banddata = np.where(banddata == 0, 30, 0)
            result_ds.GetRasterBand(band + 1).WriteArray(banddata, 0, y)
            progress(y / ysize)
    progress(1.1)
    return result_ds


def perfect_raster(raster_ds, mask_ds, outfile):
    # 获取栅格数据的基本信息improve
    raster_prj = raster_ds.GetProjection()
    raster_geo = raster_ds.GetGeoTransform()
    bandCount = raster_ds.RasterCount
    # 创建输出影像
    result_ds = gdal.GetDriverByName('MEM').CreateCopy(" ", raster_ds, strict=1)
    result_ds.SetProjection(raster_prj)
    result_ds.SetGeoTransform(raster_geo)
    tmp = subsat(raster_ds, mask_ds, result_ds, block_size=500)
    result = gdal.GetDriverByName('GTiff').CreateCopy(outfile, tmp, strict=1)
    result.FlushCache()
    result_ds = None
    tmp = None
    result = None
    return 1


def shp2raster(raster_ds, shp_layer):
    # 获取栅格数据的基本信息
    raster_prj = raster_ds.GetProjection()
    raster_geo = raster_ds.GetGeoTransform()
    # 根据输入栅格数据矢量化栅格
    x_size = raster_ds.RasterXSize
    y_size = raster_ds.RasterYSize
    # 创建mask
    mask_ds = gdal.GetDriverByName('MEM').Create(' ', int(x_size), int(y_size), 1, gdal.GDT_UInt16)
    mask_ds.SetProjection(raster_prj)
    mask_ds.SetGeoTransform(raster_geo)
    # 矢量栅格化
    print('Begin shape to mask')
    gdal.RasterizeLayer(mask_ds, [1], shp_layer, burn_values=[1], callback=progress)
    return mask_ds


def searchfiles(dirpath, partfileinfo='*', recursive=False):
    """列出符合条件的文件（包含路径），默认不进行递归查询，当recursive为True时同时查询子文件夹"""
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


def main(file_dir, shp_dir, out_dir):
    # 搜索所有需要处理的shp
    shp_files = searchfiles(shp_dir, partfileinfo="*.shp")
    # 循环shp找到对应影像进行填充
    count = 0
    for shp in shp_files:
        shp_basename = os.path.splitext(os.path.basename(shp))[0]
        img_id = shp_basename.split("xiaomai_")[1]
        # 搜索对应的影像
        file = searchfiles(file_dir, partfileinfo='*' + img_id + "*.tif")[0]
        # 开始填充
        out_path = os.path.join(out_dir, os.path.basename(file))
        # 打开栅格
        raster_ds = gdal.Open(file)
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
            shp_lyr = None
        else:
            re_shp_ds, re_shp_l = rpj_vec(shp_lyr, raster_srs)
        mask_ds = shp2raster(raster_ds, re_shp_l)
        # 根据绘制矢量填充分类结果
        res = perfect_raster(raster_ds, mask_ds, out_path)
        mask_ds = None
        shp_ds = None
        raster_ds = None
        dst_ds = None
        count += 1
        progress(count / len(shp_files))
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
    in_img_dir = r"\\192.168.0.234\nydsj\project\2.zhiyan\2.2019\6.class_result\xiaomai\class_clip"
    in_shp_dir = r"\\192.168.0.234\nydsj\project\2.zhiyan\2.2019\6.class_result\xiaomai\人工修正\补小麦"
    out_img_dir = r"\\192.168.0.234\nydsj\project\9.Insurance_gongyi\2019年\3.class_result\GJ\820208_xiaomai1.tif"
    # in_file = sys.argv[1]
    # in_shp = sys.argv[2]
    # outpath = sys.argv[3]
    main(in_img_dir, in_shp_dir, out_img_dir)

    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
