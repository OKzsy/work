#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2026/07/04 11:56
# @Author  : zhaoss
# @FileName: clipforshp.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
不以最小重叠矩形为输出结果，以矢量范围为输出结果, 保证每个县的输出结果是完整的。
Parameters

"""
import os
import sys
import time
import glob
import numpy as np
import fnmatch
import math
import tempfile
import shutil
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def searchfiles(dirpath, partfileinfo="*", recursive=False):
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
    mem_dri = ogr.GetDriverByName("Memory")
    mem_ds = mem_dri.CreateDataSource(" ")
    outLayer = mem_ds.CreateLayer(" ", geom_type=lyr.GetGeomType(), srs=srs)
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
    off_ulx, off_uly = map(
        round, gdal.ApplyGeoTransform(raster_inv_geo, extent[0], extent[3])
    )
    # 右下
    off_drx, off_dry = map(
        round, gdal.ApplyGeoTransform(raster_inv_geo, extent[1], extent[2])
    )
    # 判断是否有重叠区域
    if off_ulx >= x_size or off_uly >= y_size or off_drx <= 0 or off_dry <= 0:
        return None
        # sys.exit("Have no overlap")
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


def tif_merge(in_path_list, out_path, temp_dir, in_nodata, out_nodata):
    """影像镶嵌"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".vrt", delete=False, dir=temp_dir
    ) as tmp:
        vrt_file = tmp.name
    in_file_list = [str(file) for file in in_path_list]
    vrt_options = gdal.BuildVRTOptions(
        srcNodata=str(in_nodata), VRTNodata=str(out_nodata), hideNodata=True
    )
    gdal.BuildVRT(vrt_file, in_file_list, options=vrt_options)
    out_driver = gdal.GetDriverByName("GTiff")
    if os.path.exists(out_path):
        out_driver.Delete(out_path)
    vrt_ds = gdal.Open(vrt_file)
    out_ds = out_driver.CreateCopy(out_path, vrt_ds, callback=progress)
    out_ds.FlushCache()
    out_ds = vrt_ds = None
    return None


def main(shp_folder, raster_floder, out_folder):

    # 以县区边界为依据，重构分类结果
    area_shapefile = searchfiles(shp_folder, partfileinfo="*.shp")
    # 逐一重构
    for iarea_file in area_shapefile:
        temp_dir = tempfile.mkdtemp(dir=out_folder, prefix="Rebuild_")
        # 查找对应的分类结果文件
        shp_basename = os.path.splitext(os.path.basename(iarea_file))[0]
        area_name = shp_basename.split("_")[1]
        partfileinfo = f"*{area_name}*.tif"
        class_raster = searchfiles(raster_floder, partfileinfo=partfileinfo)[0]
        # 打开矢量文件
        shp_ds = ogr.Open(iarea_file)
        shp_lyr = shp_ds.GetLayer()
        shp_sr = shp_lyr.GetSpatialRef()
        tiff_drv = gdal.GetDriverByName("GTiff")
        # 打开栅格和矢量影像
        basename = os.path.basename(class_raster)
        raster_ds = gdal.Open(class_raster)
        raster_prj = raster_ds.GetProjection()
        raster_geo = raster_ds.GetGeoTransform()
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
        # 以栅格为基准，计算以shp为目标的栅格影像
        xmin, xmax, ymin, ymax = re_shp_l.GetExtent()
        shp_geo = [xmin, raster_geo[1], 0, ymax, 0, raster_geo[5]]
        # 计算shp对应栅格的行列数
        shp_x_xize = int(math.ceil((xmax - xmin) / abs(raster_geo[1])))
        shp_y_xize = int(math.ceil((ymax - ymin) / abs(raster_geo[5])))
        # 创建输出影像
        out_basename = basename.replace(".tif", "_fullextend.tif")
        temp_out_path = os.path.join(temp_dir, out_basename)
        out_ds = tiff_drv.Create(
            temp_out_path, shp_x_xize, shp_y_xize, 1, gdal.GDT_Byte
        )
        out_ds.SetGeoTransform(shp_geo)
        out_ds.SetProjection(raster_prj)
        # 先将shp栅格化，并填充为150
        gdal.RasterizeLayer(out_ds, [1], re_shp_l, burn_values=[150])
        out_ds.FlushCache()
        # 利用镶嵌将两个影像合并为一个，且raster位置要靠后，即有效数据覆盖无效数据
        out_path = os.path.join(out_folder, out_basename)
        in_file_list = [temp_out_path, class_raster]
        tif_merge(in_file_list, out_path, temp_dir, 0, 0)
        raster_ds = None
        out_ds = None
        shutil.rmtree(temp_dir)
        shp_lyr = None
        shp_ds = None

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
    shp_folder = r"F:\cotton\ner_sample_result\south_shp"
    raster_folder = r"F:\cotton\ner_sample_result\2025\south_2025\S2_Clip_Merge"
    out_folder = r"F:\cotton\ner_sample_result\2025\south_2025\rebuild"
    main(shp_folder, raster_folder, out_folder)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
