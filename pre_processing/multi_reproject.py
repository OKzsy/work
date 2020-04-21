#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/6/20 17:34
# @Author  : zhaoss
# @FileName: multi_reproject.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""
import os
import glob
import gc
import time
import fnmatch
import string
import random
from functools import partial
import multiprocessing as mp
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


def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def def_prj(src_dst, prj):
    # 根据目标大小，在内存创建结果影像
    tmp_dst_path = r'/vsimem/tmp_dst_{}.tiff'.format(id_generator)
    gdal.Translate(tmp_dst_path, src_dst, format='GTiff', outputSRS=prj)
    tmp_dst = gdal.Open(tmp_dst_path)
    src_dst = None
    gdal.Unlink(tmp_dst_path)
    gc.collect()
    return tmp_dst


def reproject_dataset(out_dir, src_file):
    """
    :param src_ds: 待重采样影像的数据集
    :return: 调用ReprojectImage对影像进行重采样，重采样后影像的分辨率为原始影像分辨率，
    投影信息为WGS84。
    """
    # 定义目标投影
    oSRS = osr.SpatialReference()
    # oSRS.SetWellKnownGeogCS("WGS84")
    oSRS.ImportFromEPSG(3857)
    # 对无投影的影像定义投影
    # 定义赋值投影
    src_ds = gdal.Open(src_file)
    odefprj = osr.SpatialReference()
    odefprj.ImportFromEPSG(4526)
    src_dst_prj = def_prj(src_ds, odefprj)
    src_ds = None
    # 获取原始投影
    src_prj = src_dst_prj.GetProjection()
    oSRC = osr.SpatialReference()
    oSRC.ImportFromWkt(src_prj)
    # 测试投影转换
    oSRC.SetTOWGS84(0, 0, 0)
    tx = osr.CoordinateTransformation(oSRC, oSRS)

    # 获取原始影像的放射变换参数
    geo_t = src_dst_prj.GetGeoTransform()
    x_size = src_dst_prj.RasterXSize
    y_size = src_dst_prj.RasterYSize
    bandCount = src_dst_prj.RasterCount
    dataType = src_dst_prj.GetRasterBand(1).DataType
    if oSRC.GetAttrValue("UNIT").lower() in ["metre", "meter"]:
        new_x_size = geo_t[1]
        new_y_size = geo_t[5]
    else:
        new_x_size = geo_t[1] * 10 ** 5
        new_y_size = geo_t[5] * 10 ** 5
    # 获取影像的四个角点地理坐标
    # 左上
    old_ulx, old_uly = corner_to_geo(0, 0, src_dst_prj)
    # 右上
    old_urx, old_ury = corner_to_geo(x_size, 0, src_dst_prj)
    # 左下
    old_dlx, old_dly = corner_to_geo(0, y_size, src_dst_prj)
    # 右下
    old_drx, old_dry = corner_to_geo(x_size, y_size, src_dst_prj)

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
    basename = os.path.splitext(os.path.basename(src_file))[0]
    out_path = os.path.join(out_dir, basename) + "-prj.tif"
    mem_drv = gdal.GetDriverByName('GTiff')
    # 根据计算的参数创建存储空间
    dest = mem_drv.Create(out_path, int((lrx - ulx) / new_x_size), \
                          int((uly - lry) / -new_y_size), bandCount, dataType)
    # 计算新的放射变换参数
    new_geo = (ulx, new_x_size, geo_t[2], uly, geo_t[4], new_y_size)
    # 为重投影结果设置空间参考
    dest.SetGeoTransform(new_geo)
    dest.SetProjection(oSRS.ExportToWkt())
    # 执行重投影和重采样
    res = gdal.ReprojectImage(src_dst_prj, dest, \
                              src_prj, oSRS.ExportToWkt(), \
                              gdal.GRA_NearestNeighbour)
    src_dst_prj = None
    dest = None
    gc.collect()
    return 1


def main(in_dir, out_dir, partfileinfo):
    # 搜索需要处理的影像
    Pending_images = searchfiles(in_dir, partfileinfo=partfileinfo)
    # 建立多个进程
    pool = mp.Pool(processes=5)
    func = partial(reproject_dataset, out_dir)
    for ifile in Pending_images:
        # 重投影
        pool.apply_async(func, args=(ifile,))
    pool.close()
    pool.join()
    return None


if __name__ == '__main__':
    # 支持中文路径
    gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
    # 注册所有gdal驱动
    gdal.AllRegister()
    start_time = time.clock()
    in_dir = r"\\192.168.0.234\nydsj\user\WangShun\gongyi\Data\images"
    out_dir = r"\\192.168.0.234\nydsj\user\ZSS\test\out"
    partfileinfo = "*.tif"
    main(in_dir, out_dir, partfileinfo)
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
