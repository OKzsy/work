#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2025/08/02 16:27
# @Author  : zhaoss
# @FileName: create_simplepoly.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
根据特定条件，创建对应的矢量多边形，并对矢量多边形进行简化
Parameters

"""

import os
import time
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


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
    if out_driver.TestCapability(
        ogr.ODrCCreateDataSource
    ) and out_driver.TestCapability(ogr.ODrCDeleteDataSource):
        if out_driver.TestCapability(ogr.ODrCDeleteDataSource):
            out_driver.DeleteDataSource(out_shp_path)

    # 创建新的输出数据源
    out_ds = out_driver.CreateDataSource(out_shp_path)
    if out_ds is None:
        raise Exception(f"无法创建Shapefile数据源在位置: {out_shp_path}")

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
    out_ds.Destroy()


def SimplifyPolygons(mem_layer, tolerance):
    """
    简化多边形
    :param mem_layer: 内存矢量图层
    :param tolerance: 简化容差
    :return:
    """
    for feature in mem_layer:
        geom = feature.GetGeometryRef()
        if geom is not None:
            simplified_geom = geom.SimplifyPreserveTopology(tolerance)
            feature.SetGeometry(simplified_geom)
        mem_layer.SetFeature(feature)
    return mem_layer


def main(src, dst):
    """
    将栅格文件矢量化为矢量文件
    :param src: 输入栅格文件路径
    :param dst: 输出矢量文件路径
    :return:
    """
    # 打开栅格文件
    src_ds = gdal.Open(src, gdal.GA_ReadOnly)
    if src_ds is None:
        print("无法打开栅格文件")
        return
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
    src_ds = None
    # 获取mem_ds栅格文件的波段
    band = mem_ds.GetRasterBand(1)
    # 将band中的数组转换为0和1的数组
    arr = band.ReadAsArray()
    arr[arr > 0] = 1
    # 将数组写回波段
    band.WriteArray(arr)
    band.FlushCache()
    # 设置band的无效值
    band.SetNoDataValue(0)
    # 在内存中创建临时矢量文件
    if float(gdal.__version__[0:4]) < 3.11:
        tmp_ds = ogr.GetDriverByName("Memory").CreateDataSource("temp")
    else:
        tmp_ds = ogr.GetDriverByName("MEM").CreateDataSource("temp")
    if tmp_ds is None:
        print("无法创建临时矢量文件")
        return
    # 创建矢量图层
    tmp_layer = tmp_ds.CreateLayer("polygonize", srs, ogr.wkbPolygon)
    if tmp_layer is None:
        print("无法创建矢量图层")
        return
    # 创建字段定义
    fd = ogr.FieldDefn("DN", ogr.OFTInteger)
    tmp_layer.CreateField(fd)
    # 执行矢量化操作
    gdal.Polygonize(band, band.GetMaskBand(), tmp_layer, 0, [], callback=None)
    # 按照3倍原始影像分辨率对生成的矢量文件使用SimplifyPreserveTopology函数简化多边形
    # 获取src影像的分辨率
    gt = mem_ds.GetGeoTransform()
    pixel_width = gt[1]
    pixel_height = gt[5]
    # 计算简化阈值
    simplify_threshold = 3 * max(abs(pixel_width), abs(pixel_height))
    # 简化多边形
    layer = SimplifyPolygons(tmp_layer, simplify_threshold)
    # 将内存中的矢量文件写入到目标文件中
    save_memory_layer_to_disk(layer, dst)
    # 关闭数据集
    tmp_ds = None
    tmp_layer = None
    layer = None
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
    src_file = r"E:\1.phdFile\sateliteData\GF1_atm\temp\GF2_PMS2_E114.0_N31.9_20241214_L1A14314296001-MSS2_ort_atm.tif"
    dst_shp = r"E:\1.phdFile\sateliteData\GF1_atm\temp\GF2_PMS2_E114.0_N31.9_20241214_L1A14314296001-MSS2_ort_atm.shp"
    main(src_file, dst_shp)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
