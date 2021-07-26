#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2021/5/11 17:35
# @Author  : zhaoss
# @FileName: index_tatistics.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
利用网格化的地块数据分别统计每个地块的指数平均值，并写入数据库

Parameters


"""

import os
import sys
import glob
import time
import psycopg2
import fnmatch
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


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
    # out = r"F:\test_data\clipraster\gdal_mask2\test3.tif"
    # mask_ds = gdal.GetDriverByName('GTiff').Create(out, int(x_size), int(y_size), 1, gdal.GDT_Byte)
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


def mask_raster(raster_ds, mask_ds, ext):
    # 将行列整数浮点化
    ext = np.array(ext) * 1.0
    # 获取栅格数据的基本信息
    raster_geo = raster_ds.GetGeoTransform()
    bandCount = raster_ds.RasterCount
    dataType = raster_ds.GetRasterBand(1).DataType
    # 根据最小重叠矩形的范围进行矢量栅格化
    ulx, uly = gdal.ApplyGeoTransform(raster_geo, ext[0], ext[1])
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


def average(data):
    nozero_index = np.where(data != 0)
    nozero_num = nozero_index[0].shape[0]
    ave = np.sum(data[nozero_index]) / nozero_num
    return round(ave, 4)


def write2database(fieldName, fieldData):
    # 连接数据库
    conn = psycopg2.connect(database="WebGis", user="sa", password="Nydsj@222", host="192.168.0.250", port="5432")
    cur = conn.cursor()
    insert_str = "INSERT INTO crop_index ({}) VALUES ({})".format(','.join(fieldName), ','.join(fieldData))
    cur.execute(insert_str)
    conn.commit()
    return None


def main(shp, vi_floder):
    # 判断vi_dir是路径还是文件
    if os.path.isdir(vi_floder):
        rasters = searchfiles(vi_floder, partfileinfo='*dahutuo_fc.tif')
    else:
        rasters = [vi_floder]
    for raster in rasters:
        # 打开栅格和矢量影像
        raster_ds = gdal.Open(raster)
        shp_ds = ogr.Open(shp)
        shp_lyr = shp_ds.GetLayer()
        shp_sr = shp_lyr.GetSpatialRef()
        # 获取影像名称
        raster_basename = os.path.splitext(os.path.basename(raster))[0]
        raster_basename_elements = raster_basename.split('_')
        date_element = raster_basename_elements[2]
        date_str = '-'.join([date_element[0:4], date_element[4:6], date_element[6:8]])

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
        # 拆分矢量用以对单个要素进行裁剪
        # 定义变量用以显示进度条
        count = 0
        num_feature = re_shp_l.GetFeatureCount()
        for feat in re_shp_l:
            id = feat.GetField('Name')
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
            res = mask_raster(raster_ds, mask_ds, offset)
            # 统计参数，此处为计算平均值
            ave = average(res)
            # 写入数据库
            field_name = ['date', 'type', 'avg', 'id']
            field_data = [repr(k) for k in [date_str, 'fc', str(ave), str(int(id))]]
            write2database(field_name, field_data)
            progress((count + 1) / num_feature)
            count += 1
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
    start_time = time.time()
    shp_file = r"\\192.168.0.234\nydsj\project\39.鹤壁高标准良田\2.vector\3.人工勾画\地块划分\大滹沱村地块划分-上图.shp"
    vi_dir = r"\\192.168.0.234\nydsj\project\39.鹤壁高标准良田\4.监测\2.长势data\2.coverage"
    main(shp_file, vi_dir)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
