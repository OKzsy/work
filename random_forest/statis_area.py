#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2026/07/03 21:44
# @Author  : zhaoss
# @FileName: statis_area.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
针对完成后的区域分类识别结果进行统计
Parameters

"""

import os
import time
import glob
import sys
import fnmatch
import tempfile
import shutil
import numpy as np
import numba as nb
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


@nb.njit(cache=True)
def compare_analysis(data):
    """对输入的两个数据进行对比分析，返回对比后统计的结果"""
    # 初始统计量
    tcotton_count = 0
    lcotton_count = 0
    increase_count = 0
    decrease_count = 0
    stable_count = 0
    # 获取行列
    n_samples = data.shape[0]
    for i in range(n_samples):
        tvalue = data[i][0]
        lvalue = data[i][1]
        # 进行统计
        if tvalue == 100:
            tcotton_count += 1
        if lvalue == 100:
            lcotton_count += 1
        # 变化统计
        if tvalue == 100 and lvalue == 100:
            # 稳定
            stable_count += 1
            continue
        if tvalue == 101 and lvalue == 100:
            # 今年非棉花，去年棉花，减少
            decrease_count += 1
            continue
        if tvalue == 100 and lvalue == 101:
            # 今年棉花，去年非棉花，增加
            increase_count += 1
            continue

    return (
        tcotton_count,
        lcotton_count,
        increase_count,
        decrease_count,
        stable_count,
    )


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
    mask_ds = gdal.GetDriverByName("MEM").Create(
        "", int(x_size), int(y_size), 1, gdal.GDT_Byte
    )
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
        banddata = raster_ds.GetRasterBand(band + 1).ReadAsArray(
            int(ext[0]), int(ext[1]), int(x_size), int(y_size)
        )
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


def tif_clip(file, shp, out_dir, nodata=None):
    out_dir = tempfile.mkdtemp(dir=out_dir, prefix="CLIP_")
    # 判断输入的是否为文件
    if os.path.isdir(file):
        rasters = searchfiles(file, partfileinfo="*.tif")
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
        mem_dri = ogr.GetDriverByName("Memory")
        temp_shp_ds = mem_dri.CreateDataSource(" ")
        new_shp_l = temp_shp_ds.CopyLayer(re_shp_l, "new_shp_l")
        # 计算矢量和栅格的最小重叠矩形
        offset = min_rect(raster_ds, new_shp_l)
        if offset is None:
            continue
        # 创建输出影像
        out = os.path.join(out_dir, basename).replace(".tif", "_clip.tif")
        ulx, uly = gdal.ApplyGeoTransform(raster_geo, offset[0], offset[1])
        result_ds = gdal.GetDriverByName("GTiff").Create(
            out, int(offset[2]), int(offset[3]), bandCount, dataType
        )
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
        progress(1.0)
        temp_shp_ds = None
        new_shp_l = None
        re_shp_ds = None
        raster_ds = None
    shp_ds = None
    shp_lyr = None
    return out


def main(tfloder, lfloder, shp_path, statis_file):
    """
    以时间靠后的年份县域分类结果数据为依据，查找对应县域上一年度分类结果数据进行对比分析
    """
    # 按照区域矢量查找对应的前后两年结果数据
    area_shapefile = searchfiles(shp_path, partfileinfo="*.shp")
    temp_dir = tempfile.mkdtemp(dir=os.path.dirname(statis_file), prefix="MERGE_")
    # 打开结果文件用以写入统计结果，统计结果以亩为单位
    fj = open(statis_file, mode="w", encoding="utf-8")
    line = [
        "序号",
        "country",
        "今年棉花面积",
        "去年棉花面积",
        "稳定种植棉花面积",
        "增加面积",
        "减少面积",
    ]
    fj.write(",".join(line) + "\n")
    serial = 0
    # 逐个对比分析
    for iarea_file in area_shapefile:
        shp_basename = os.path.splitext(os.path.basename(iarea_file))[0]
        # area_name = shp_basename.split("_")[1]
        area_name = shp_basename
        partfileinfo = f"*{area_name}*.tif"
        print(f"{area_name}")
        this_year_file = searchfiles(tfloder, partfileinfo=partfileinfo)[0]
        if not this_year_file:
            print(f"Can't find this year class file for:{area_name}")
            continue
        # 查找对应的上一年度结果
        last_year_file = searchfiles(lfloder, partfileinfo=partfileinfo)[0]
        if not last_year_file:
            print(f"Can't find last year class file for:{area_name}")
            continue
        # 防止两年结果大小不一致，无法进行逐像元计算，增加裁剪过程
        nodata = 0
        this_year_reclip_file = tif_clip(this_year_file, iarea_file, temp_dir, nodata)
        last_year_reclip_file = tif_clip(last_year_file, iarea_file, temp_dir, nodata)
        # 打开影像，获取数据，用于对比
        this_ds = gdal.Open(this_year_reclip_file)
        this_x_size = this_ds.RasterXSize
        this_y_size = this_ds.RasterYSize
        geo = this_ds.GetGeoTransform()
        this_band = this_ds.GetRasterBand(1)
        this_arr = this_band.ReadAsArray()
        last_ds = gdal.Open(last_year_reclip_file)
        last_x_size = last_ds.RasterXSize
        last_y_size = last_ds.RasterYSize
        last_band = last_ds.GetRasterBand(1)
        last_arr = last_band.ReadAsArray()
        x_size = min(this_x_size, last_x_size)
        y_size = min(this_y_size, last_y_size)
        all_data = np.empty((2, y_size, x_size), dtype=np.uint8)
        all_data[0] = this_arr[0:y_size, 0:x_size]
        all_data[1] = last_arr[0:y_size, 0:x_size]
        # 释放资源
        this_arr = None
        last_arr = None
        last_band = None
        last_ds = None
        this_band = None
        this_ds = None
        # 对比分析
        all_data_T = all_data.reshape(2, y_size * x_size).T
        all_data = None
        # 统计结果(tcotton_count,lcotton_count,increase_count,decrease_count,stable_count,check_count)
        compare_res = compare_analysis(all_data_T)
        # 计算各个面积，写入结果文件，序号，country，今年棉花面积，去年棉花面积，稳定种植棉花面积，增加面积，减少面积
        serial += 1
        # 面积系数
        area_factor = geo[1] * abs(geo[5])
        line = [
            str(serial),
            area_name,
            f"{compare_res[0] * area_factor / 666.7:.2f}",
            f"{compare_res[1] * area_factor / 666.7:.2f}",
            f"{compare_res[4] * area_factor / 666.7:.2f}",
            f"{compare_res[2] * area_factor / 666.7:.2f}",
            f"{compare_res[3] * area_factor / 666.7:.2f}",
        ]
        fj.write(",".join(line) + "\n")
    fj.close()
    shutil.rmtree(temp_dir)
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
    region = "north"
    this_year_folder = r"F:\cotton\finalMap\2026\north-30"
    last_year_folder = r"F:\cotton\finalMap\2025\north-30"
    shp_folder = rf"\\192.168.62.7\zhaoss\棉花\矢量范围\single_pol\pol4class\{region}"
    statis_txt = rf"F:\cotton\finalMap\{region}-30.txt"
    main(this_year_folder, last_year_folder, shp_folder, statis_txt)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
