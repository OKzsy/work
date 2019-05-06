#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/3/6 15:10
# @Author  : zhaoss
# @FileName: GF2_sha_clip.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
    用以批量的对融合结果的nodata区域进行裁剪

Parameters


"""
import os
import sys
import glob
import fnmatch
import numpy as np
import time
import datetime
import numba as nb
import multiprocessing.dummy as mp
from functools import partial
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


@nb.jit
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


def clip_file(shp_path, out, file):
    # 打开栅格和矢量影像
    shp_ds = ogr.Open(shp_path)
    shp_ly = shp_ds.GetLayer()
    # 获取影像名称
    tifbasename = os.path.basename(file)
    print("{0} is assigned to: {1}".format(file, os.getpid()))
    print("The {0} start time is: {1}".format(os.getpid(), datetime.datetime.now()))
    # 拆分矢量用以对单个要素进行裁剪
    # 定义变量用以显示进度条
    shp_ly.ResetReading()
    for feat in shp_ly:
        # 获取要素的属性值用以确定需要处理的融合影像名称
        basenamewithoutext = os.path.splitext(feat.filename)[0]
        basenamewithoutext = os.path.splitext(basenamewithoutext)[0]
        basenames = basenamewithoutext.split('_')
        sha_name = '_'.join([basenames[0], basenames[4], basenames[5], 'sha']) + '.tif'
        # 判断要素是否对应
        if not tifbasename == sha_name:
            continue
        else:
            # 打开栅格
            raster_ds = gdal.Open(file)
            # 获取栅格投影
            raster_srs_wkt = raster_ds.GetProjection()
            raster_srs = osr.SpatialReference()
            raster_srs.ImportFromWkt(raster_srs_wkt)
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
            outpath = os.path.join(out, sha_name)
            res = mask_raster(raster_ds, mask_ds, outpath, offset)
            raster_ds = None
    shp_ds = None
    print("The {0} end time is: {1}".format(os.getpid(), datetime.datetime.now()))
    return None


def main(raster_path, shp, out):
    # 寻找文件
    file_lists = searchfiles(raster_path, '*sha.tif')

    func = partial(clip_file, shp, out)
    # pool = mp.Pool(processes=3)
    for ifile in file_lists:
        clip_file(shp, out, ifile)
        # res = pool.apply_async(func, args=(ifile, ))
    # pool.close()
    # pool.join()
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
    # in_file = r"\\192.168.0.234\nydsj\user\GF2\sha\yucheng\new"
    # shpfile = r"\\192.168.0.234\nydsj\project\11.邓州_正阳小麦\2.vector\2.数据情况\GF2\周口\GF_虞城.shp"
    # outfile = r"\\192.168.0.234\nydsj\user\GF2\clip\yucheng"
    in_file = sys.argv[1]
    shpfile = sys.argv[2]
    outfile = sys.argv[3]
    main(in_file, shpfile, outfile)
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
