#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/4/17 15:39
# @Author  : zhaoss
# @FileName: reproject.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
    将输入的影像重采样为指定的投影，默认为WGS84

Parameters
    partfileinfo : 正则表达式，搜索出需处理的影像
    in_dir       : 待重采样影像的路径
    out_dir      : 影像输出路径


"""

import os
import glob
import gc
import time
import fnmatch
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


def corner_to_geo(sample, line, dataset):
    """
    :param sample: 列号
    :param line:   行号
    :param dataset: 所在影像的数据集
    :return: 指定行列号的经纬度
    """
    # 计算指定行,列号的地理坐标
    Geo_t = dataset.GetGeoTransform()
    # 计算地理坐标
    geoX = Geo_t[0] + sample * Geo_t[1]
    geoY = Geo_t[3] + line * Geo_t[5]
    return geoX, geoY


def reproject_dataset(src_ds):
    """
    :param src_ds: 待重采样影像的数据集
    :return: 调用ReprojectImage对影像进行重采样，重采样后影像的分辨率为原始影像分辨率，
    投影信息为WGS84。
    """
    # 定义目标投影
    oSRS = osr.SpatialReference()
    # oSRS.SetWellKnownGeogCS("WGS84")
    # oSRS.ImportFromEPSG(3857)
    oSRS.ImportFromEPSG(4526)
    # 获取原始投影
    src_prj = src_ds.GetProjection()
    oSRC = osr.SpatialReference()
    oSRC.ImportFromWkt(src_prj)
    # 测试投影转换
    oSRC.SetTOWGS84(0, 0, 0)
    tx = osr.CoordinateTransformation(oSRC, oSRS)

    # 获取原始影像的放射变换参数
    geo_t = src_ds.GetGeoTransform()
    x_size = src_ds.RasterXSize
    y_size = src_ds.RasterYSize
    bandCount = src_ds.RasterCount
    dataType = src_ds.GetRasterBand(1).DataType
    if oSRC.GetAttrValue("UNIT") == "metre":
        new_x_size = geo_t[1] * 10 ** (-5)
        new_y_size = geo_t[5] * 10 ** (-5)
    else:
        new_x_size = geo_t[1]
        new_y_size = geo_t[5]
    # 获取影像的四个角点地理坐标
    # 左上
    old_ulx, old_uly = corner_to_geo(0, 0, src_ds)
    # 右上
    old_urx, old_ury = corner_to_geo(x_size, 0, src_ds)
    # 左下
    old_dlx, old_dly = corner_to_geo(0, y_size, src_ds)
    # 右下
    old_drx, old_dry = corner_to_geo(x_size, y_size, src_ds)

    # 计算出新影像的边界
    # 左上
    (new_ulx, new_uly, new_ulz) = tx.TransformPoint(old_ulx, old_uly, 0)
    # 右上
    (new_urx, new_ury, new_urz) = tx.TransformPoint(old_urx, old_ury, 0)
    # 左下
    (new_dlx, new_dly, new_dlz) = tx.TransformPoint(old_dlx, old_dly, 0)
    # 右下
    (new_drx, new_dry, new_drz) = tx.TransformPoint(old_drx, old_dry, 0)
    # 统计出新影像的范围
    # 左上经度
    ulx = min(new_ulx, new_dlx)
    # 左上纬度
    uly = max(new_uly, new_ury)
    # 右下经度
    lrx = max(new_urx, new_drx)
    # 右下纬度
    lry = min(new_dly, new_dry)
    # 创建重投影后新影像的存储位置
    mem_drv = gdal.GetDriverByName('MEM')
    # 根据计算的参数创建存储空间
    dest = mem_drv.Create('', int((lrx - ulx) / new_x_size), \
                          int((uly - lry) / -new_y_size), bandCount, dataType)
    # 计算新的放射变换参数
    new_geo = (ulx, new_x_size, geo_t[2], uly, geo_t[4], new_y_size)
    # 为重投影结果设置空间参考
    dest.SetGeoTransform(new_geo)
    dest.SetProjection(oSRS.ExportToWkt())
    # 执行重投影和重采样
    print('Begin to reprojection and resample!')
    res = gdal.ReprojectImage(src_ds, dest, \
                              src_prj, oSRS.ExportToWkt(), \
                              gdal.GRA_NearestNeighbour, callback=progress)
    return dest


def main(in_dir, out_dir, partfileinfo):
    # 搜索需要处理的影像
    Pending_images = searchfiles(in_dir, partfileinfo=partfileinfo)
    # 开始重采样
    count = 1
    for ifile in Pending_images:
        print("A total of {} scene images, this is the {}".format(len(Pending_images), count))
        count += 1
        # 获取影像的名称
        basename = os.path.splitext(os.path.basename(ifile))[0]
        # 打开影像
        dataset = gdal.Open(ifile)
        # 重投影
        dest = reproject_dataset(dataset)
        # 拼接输出影像绝对路径
        out_img_path = os.path.join(out_dir, basename) + "-prj.tif"
        # 存储经重采样的结果
        print('Store the reprojected image!')
        driver = gdal.GetDriverByName("GTiff")
        dst_ds = driver.CreateCopy(out_img_path, dest, callback=progress)
        # 释放资源
        dataset = None
        dest = None
        dst_ds = None
        gc.collect()
    return None


if __name__ == '__main__':
    # 支持中文路径
    gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
    # 注册所有gdal驱动
    gdal.AllRegister()
    start_time = time.clock()
    in_dir = r"F:\test\20190816_out"
    out_dir = r"F:\test\20190816_out"
    partfileinfo = "S2_20180816.tif"
    main(in_dir, out_dir, partfileinfo)
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
