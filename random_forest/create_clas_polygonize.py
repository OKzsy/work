#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2026/06/28 19:12
# @Author  : zhaoss
# @FileName: create_clas_polygonize.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
将栅格影像中的目标值转换为矢量
Parameters

"""

import os
import time
import fnmatch
import glob
import gc
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def searchfiles(dirpath, partfileinfo="*", recursive=False):
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


def save_memory_layer_to_disk(mem_layer, out_shp_path):
    """
    将内存中的矢量图层保存到磁盘上的Shapefile文件。

    :param mem_layer: 内存中的矢量图层，类型为ogr.Layer
    :param out_shp_path: 输出Shapefile的完整路径，类型为str
    :return: 无返回值
    """
    # 创建一个Shapefile驱动
    out_driver = ogr.GetDriverByName("ESRI Shapefile")

    # 如果已存在同名文件，删除它
    if os.path.exists(out_shp_path):
        if out_driver.TestCapability(
            ogr.ODrCCreateDataSource
        ) and out_driver.TestCapability(ogr.ODrCDeleteDataSource):
            if out_driver.TestCapability(ogr.ODrCDeleteDataSource):
                out_driver.DeleteDataSource(out_shp_path)

    # 创建新的输出数据源
    out_ds = out_driver.CreateDataSource(out_shp_path)
    if not out_ds:
        raise IOError(f"无法创建Shapefile数据源在位置: {out_shp_path}")

    # 获取内存图层的空间参考
    spatial_ref = mem_layer.GetSpatialRef()

    # 复制图层定义（包括几何类型）
    out_layer = out_ds.CreateLayer(
        "output_layer", spatial_ref, geom_type=mem_layer.GetGeomType()
    )
    if out_layer is None:
        raise Exception(f"无法在数据源中创建图层在位置: {out_shp_path}")

    # 复制字段定义
    for i in range(mem_layer.GetLayerDefn().GetFieldCount()):
        field_defn = mem_layer.GetLayerDefn().GetFieldDefn(i)
        out_layer.CreateField(field_defn)

    # 复制特征
    for in_feature in mem_layer:
        out_feature = ogr.Feature(out_layer.GetLayerDefn())
        for i in range(out_feature.GetFieldCount()):
            out_feature.SetField(i, in_feature.GetField(i))
        geom = in_feature.GetGeometryRef().Clone()
        if geom is not None:
            out_feature.SetGeometry(geom)
        if out_layer.CreateFeature(out_feature) != 0:
            raise Exception(f"无法在数据源中创建要素在位置: {out_shp_path}")
        out_feature.Destroy()
    # 清理资源
    out_layer = None
    out_ds = None


def SimplifyPolygons(poly_layer, simplify_threshold, min_area_sqm=1000):
    """
    简化多边形
    :param mem_layer: 内存矢量图层
    :param tolerance: 简化容差
    :return:
    """
    # 创建结果图层（同投影、同字段）
    if float(gdal.__version__[0:4]) < 3.11:
        simplified_ds = ogr.GetDriverByName("Memory").CreateDataSource("simplified")
    else:
        simplified_ds = ogr.GetDriverByName("MEM").CreateDataSource("simplified")

    spatial_ref = poly_layer.GetSpatialRef()
    geom_type = poly_layer.GetGeomType()

    simplified_layer = simplified_ds.CreateLayer(
        "simplified", spatial_ref, geom_type=geom_type
    )
    layer_defn = poly_layer.GetLayerDefn()

    # 复制字段
    for i in range(layer_defn.GetFieldCount()):
        field_defn = layer_defn.GetFieldDefn(i)
        simplified_layer.CreateField(field_defn)
    # 增加面积过滤功能
    _auth_crs = spatial_ref.GetAuthorityName(None), spatial_ref.GetAuthorityCode(None)
    unit_name = (
        spatial_ref.GetLinearUnitsName()
        if spatial_ref.IsProjected()
        else "度（地理坐标系）"
    )
    unit_factor = spatial_ref.GetLinearUnits()  # 1度 = 111319 米（近似）

    # 若为地理坐标系，给出警告
    if not spatial_ref.IsProjected():
        # 近似转换
        print(f"将使用近似转换：1 度² ≈ {(111319**2):,.0f} 平方米")
        degree_to_sqm = (111319.0) ** 2  # 粗略值
    else:
        degree_to_sqm = None
    # 遍历并简化每个 geometry
    for feature in poly_layer:
        geom = feature.GetGeometryRef()
        if not geom or geom.IsEmpty():
            continue
        try:
            # 尝试简化（保留拓扑）
            simplified_geom = geom.SimplifyPreserveTopology(simplify_threshold)
        except RuntimeError:
            simplified_geom = None
        # 过滤无效结果
        if not simplified_geom or simplified_geom.IsEmpty():
            continue
        # 计算面积（单位：坐标系单位²）
        area_unitsq = simplified_geom.GetArea()
        # 转换为平方米
        if degree_to_sqm is not None:
            area_sqm = area_unitsq * degree_to_sqm
        else:
            area_sqm = area_unitsq
        # 过滤小面积
        # if area_sqm < min_area_sqm:
        #     simplified_geom = None  # 标记跳过
        #     continue
        # 创建新要素
        out_feature = ogr.Feature(simplified_layer.GetLayerDefn())
        for i in range(feature.GetFieldCount()):
            field_name = layer_defn.GetFieldDefn(i).GetNameRef()
            if field_name == "area":
                out_feature.SetField("area", round(area_sqm / 666.67, 2))
            else:
                out_feature.SetField(i, feature.GetField(i))
        out_feature.SetGeometry(simplified_geom)
        if simplified_layer.CreateFeature(out_feature) != 0:
            print(f"Warning: Failed to create simplified feature")
        out_feature = None  # Clear

    return simplified_layer, simplified_ds


def main(file, dst):
    """
    将栅格文件矢量化为矢量文件
    :param src: 输入栅格文件路径
    :param dst: 输出矢量文件路径
    :return:
    """
    # 判断输入的是否为文件
    if os.path.isdir(file):
        rasters = searchfiles(file, partfileinfo="*.tif")
    else:
        rasters = [file]
    # 循环处理
    for raster in rasters:
        basename = os.path.splitext(os.path.basename(raster))[0]
        src_ds = gdal.Open(raster, gdal.GA_ReadOnly)
        if src_ds is None:
            print(f"Can't open the file:{basename}")
            continue
        # 获取栅格文件的投影信息
        srs = osr.SpatialReference()
        srs.ImportFromWkt(src_ds.GetProjectionRef())
        # 在内存中创建src_ds的第一波段副本，并根据src_ds的第一波段数据创建二值数据波段
        mem_ds = gdal.GetDriverByName("MEM").Create(
            "", src_ds.RasterXSize, src_ds.RasterYSize, 1, gdal.GDT_Byte
        )
        mem_ds.SetProjection(srs.ExportToWkt())
        mem_ds.SetGeoTransform(src_ds.GetGeoTransform())
        mem_ds.GetRasterBand(1).WriteArray(src_ds.GetRasterBand(1).ReadAsArray())
        mem_ds.FlushCache()
        # 获取待处理的目标波段
        pend_band = src_ds.GetRasterBand(1)
        pend_arr = pend_band.ReadAsArray()
        # 将pend_band中的数组转换为0和1的数组,0是背景,1是目标像元值
        pend_arr = (pend_arr == 100).astype(np.uint8)
        # 将二值数组写入到mem_ds中
        target_band = mem_ds.GetRasterBand(1)
        target_band.WriteArray(pend_arr)
        target_band.FlushCache()
        # 设置band的无效值
        target_band.SetNoDataValue(0)
        pend_arr = None
        del pend_band
        del src_ds
        # 在内存中创建临时矢量文件
        if float(gdal.__version__[0:4]) < 3.11:
            tmp_ds = ogr.GetDriverByName("Memory").CreateDataSource("temp")
        else:
            tmp_ds = ogr.GetDriverByName("MEM").CreateDataSource("temp")
        if tmp_ds is None:
            print(f"Can't create the shapefile:{os.path.basename(raster)}")
            continue
        # 创建矢量图层
        tmp_layer = tmp_ds.CreateLayer("polygonize", srs, ogr.wkbPolygon)
        if tmp_layer is None:
            print(f"Can't create the shapefile Layer:{os.path.basename(raster)}")
            continue
        # 创建字段定义
        fd = ogr.FieldDefn("DN", ogr.OFTInteger)
        tmp_layer.CreateField(fd)
        # 创建面积字段
        fd = ogr.FieldDefn("area", ogr.OFTReal)
        tmp_layer.CreateField(fd)
        options = ["CONNECTIVITY=8", "MERGE_TOUCHING=1"]
        # 执行矢量化操作
        gdal.Polygonize(
            target_band,
            target_band.GetMaskBand(),
            tmp_layer,
            0,
            options,
            callback=progress,
        )
        # 按照3倍原始影像分辨率对生成的矢量文件使用SimplifyPreserveTopology函数简化多边形
        # 获取src影像的分辨率
        gt = mem_ds.GetGeoTransform()
        pixel_width = gt[1]
        pixel_height = gt[5]
        # 计算简化阈值
        simplify_threshold = max(3 * max(abs(pixel_width), abs(pixel_height)), 1e-6)
        # 简化多边形
        layer, simplified_ds = SimplifyPolygons(
            tmp_layer, simplify_threshold, min_area_sqm=6600
        )
        # 将内存中的矢量文件写入到目标文件中
        out_shp = os.path.join(dst, basename + ".shp")
        save_memory_layer_to_disk(layer, out_shp)
        # 关闭矢量数据集
        tmp_layer = None
        layer = None
        tmp_ds = None
        # 关闭栅格数据集
        target_band = None
        mem_ds = None
        # 释放内存
        del tmp_ds, tmp_layer, layer, simplified_ds, mem_ds, target_band
        gc.collect()
        print("矢量化完成")

    return None


if __name__ == "__main__":
    # 支持中文路径
    gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
    # 支持中文属性字段
    gdal.SetConfigOption("SHAPE_ENCODING", "GBK")
    # 注册所有ogr驱动
    ogr.RegisterAll()
    # 注册所有gdal驱动
    gdal.AllRegister()
    start_time = time.time()
    src_dir = r"F:\cotton\finalMap\2025\south-30"
    dst_shp_dir = r"F:\cotton\finalMap\2025\south-30-shp"
    main(src_dir, dst_shp_dir)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
