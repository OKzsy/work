#!/usr/bin/env python
# -*- coding:utf-8 -*-import os
import os
import re
import sys
import glob
import shutil
import math
import fnmatch
import datetime
import tempfile
import gc
import numpy as np
import numba as nb
import multiprocessing as mp
from osgeo import gdal, ogr, osr

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress

# 支持中文路径
gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
# 支持中文属性字段
gdal.SetConfigOption("SHAPE_ENCODING", "GBK")
# 注册所有ogr驱动
ogr.RegisterAll()
# 注册所有gdal驱动
gdal.AllRegister()


def select_tif(input_list):
    output_dict = {}
    for tif_path in input_list:
        tile_match = re.search(r"T\d{2}[A-Z]{3}", tif_path)
        if not tile_match:
            print(f"Warning: 无法提取Tile编号 - {tif_path}")
            continue
        tile = tile_match.group()

        date_match = re.search(r"(\d{8})T", tif_path)
        if not date_match:
            print(f"Warning: 无法提取日期 - {tif_path}")
            continue
        date_str = date_match.group(1)
        current_date = datetime.datetime.strptime(date_str, "%Y%m%d")

        if tile not in output_dict or current_date > output_dict[tile]["date"]:
            output_dict[tile] = {"path": tif_path, "date": current_date}
    return output_dict


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


def reproject_dataset(src_file, dst_dir):
    """
    :param src_ds: 待重采样影像的数据集
    :return: 调用ReprojectImage对影像进行重采样,重采样后影像的分辨率为原始影像分辨率,
    投影信息为WGS84。
    """
    # 定义目标投影
    wkt = """
    PROJCS["Asia_North_Albers_Equal_Area_Conic",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,
    AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],
    UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],
    PROJECTION["Albers_Conic_Equal_Area"],PARAMETER["latitude_of_center",30],PARAMETER["longitude_of_center",95],
    PARAMETER["standard_parallel_1",15],PARAMETER["standard_parallel_2",65],PARAMETER["false_easting",0],PARAMETER["false_northing",0],
    UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH],AUTHORITY["ESRI","102025"]]
    """
    oSRS = osr.SpatialReference()
    oSRS.ImportFromWkt(wkt)
    # 获取原始投影
    src_ds = gdal.Open(src_file)
    src_prj = src_ds.GetProjection()
    oSRC = osr.SpatialReference()
    oSRC.ImportFromWkt(src_prj)

    # 获取原始影像的放射变换参数
    geo_t = src_ds.GetGeoTransform()
    x_size = src_ds.RasterXSize
    y_size = src_ds.RasterYSize
    bandCount = src_ds.RasterCount
    dataType = src_ds.GetRasterBand(1).DataType
    # if oSRC.GetAttrValue("UNIT") == "metre":
    #     new_x_size = geo_t[1] * 10 ** (-5)
    #     new_y_size = geo_t[5] * 10 ** (-5)
    # else:
    #     new_x_size = geo_t[1]
    #     new_y_size = geo_t[5]
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
    # 强制两者的轴顺为传统的 (X,Y) 即 (Easting, Northing)
    if int(gdal.__version__[0]) >= 3:
        oSRS.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        oSRC.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    # 测试投影转换
    oSRC.SetTOWGS84(0, 0, 0)
    tx = osr.CoordinateTransformation(oSRC, oSRS)
    # 计算出新影像的边界
    # 左上
    new_ulx, new_uly, new_ulz = tx.TransformPoint(old_ulx, old_uly, 0)
    # 右上
    new_urx, new_ury, new_urz = tx.TransformPoint(old_urx, old_ury, 0)
    # 左下
    new_dlx, new_dly, new_dlz = tx.TransformPoint(old_dlx, old_dly, 0)
    # 右下
    new_drx, new_dry, new_drz = tx.TransformPoint(old_drx, old_dry, 0)
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
    tif_drv = gdal.GetDriverByName("GTiff")
    basename = os.path.basename(src_file).replace(".tif", "_rpj.tif")
    dst_path = os.path.join(dst_dir, basename)
    # 根据计算的参数创建存储空间
    dest = tif_drv.Create(
        dst_path,
        int((lrx - ulx) / new_x_size),
        int((uly - lry) / -new_y_size),
        bandCount,
        dataType,
    )
    # 计算新的放射变换参数
    new_geo = (ulx, new_x_size, geo_t[2], uly, geo_t[4], new_y_size)
    # 为重投影结果设置空间参考
    dest.SetGeoTransform(new_geo)
    dest.SetProjection(oSRS.ExportToWkt())
    # 执行重投影和重采样
    res = gdal.ReprojectImage(
        src_ds,
        dest,
        src_prj,
        oSRS.ExportToWkt(),
        gdal.GRA_NearestNeighbour,
        # callback=progress,
    )
    # 回收资源
    src_ds = None
    dest = None
    return [dst_path]


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


def position_in_shp(offset, raster_ds, out_ds):
    # 计算最小重叠矩形在shp生成的白膜上的位置
    raster_geo = raster_ds.GetGeoTransform()
    out_geo = out_ds.GetGeoTransform()
    # 获取最小重叠矩形的左上角坐标
    ulx, uly = gdal.ApplyGeoTransform(raster_geo, offset[0], offset[1])
    # 计算逆放射变换系数
    out_inv_geo = gdal.InvGeoTransform(out_geo)
    # 计算重叠矩形的左上角坐标在白膜上的列行号
    # 左上
    off_ulx, off_uly = map(round, gdal.ApplyGeoTransform(out_inv_geo, ulx, uly))
    return off_ulx, off_uly


def class_fill(file, shp, out_dir):
    """
    将分类结果填充到由shp确定边界的结果文件中
    """
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
    tiff_drv = gdal.GetDriverByName("GTiff")
    for raster in rasters:
        basename = os.path.basename(raster)
        raster_ds = gdal.Open(raster)
        raster_prj = raster_ds.GetProjection()
        raster_geo = raster_ds.GetGeoTransform()
        bandCount = raster_ds.RasterCount
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
        # 计算矢量和栅格的最小重叠矩形
        offset = min_rect(raster_ds, re_shp_l)
        if offset is None:
            re_shp_l = None
            re_shp_ds = None
            raster_ds = None
            continue
        # 以栅格为基准，计算以shp为目标的栅格影像
        xmin, xmax, ymin, ymax = re_shp_l.GetExtent()
        shp_geo = [xmin, raster_geo[1], 0, ymax, 0, raster_geo[5]]
        # 计算shp对应栅格的行列数
        shp_x_xize = int(math.ceil((xmax - xmin) / abs(shp_geo[1])))
        shp_y_xize = int(math.ceil((ymax - ymin) / abs(shp_geo[5])))
        # 创建输出影像
        out_basename = basename.replace(".tif", "_fill.tif")
        temp_out_path = os.path.join(out_dir, out_basename)
        out_ds = tiff_drv.Create(
            temp_out_path, shp_x_xize, shp_y_xize, 1, gdal.GDT_Byte
        )
        out_ds.SetGeoTransform(shp_geo)
        out_ds.SetProjection(raster_prj)
        # 先将shp栅格化，并填充为150
        gdal.RasterizeLayer(out_ds, [1], re_shp_l, burn_values=[150])
        out_ds.FlushCache()
        # 计算重叠矩形在白膜上的位置
        point_position = position_in_shp(offset, raster_ds, out_ds)
        # 读取结果影像
        raster_band = raster_ds.GetRasterBand(1)
        class_arr = raster_band.ReadAsArray(
            int(offset[0]), int(offset[1]), int(offset[2]), int(offset[3])
        )
        # 写入白膜中
        out_xsize = out_ds.RasterXSize
        out_ysize = out_ds.RasterYSize
        real_xsize = min(int(offset[2]), out_xsize - point_position[0])
        real_ysize = min(int(offset[3]), out_ysize - point_position[1])
        out_band = out_ds.GetRasterBand(1)
        out_band.WriteArray(
            class_arr[0:real_ysize, 0:real_xsize], point_position[0], point_position[1]
        )
        out_band.FlushCache()
        out_band = None
        out_ds = None
        class_arr = None
        raster_band = None
        raster_ds = None
    shp_ds = None
    shp_lyr = None
    return [temp_out_path]


def sorted_image(files_path):
    # 按照时间顺序对影像进行排序，返回排序后的结果
    output_dict = {}
    for tif_path in files_path:
        tile_match = re.search(r"T\d{2}[A-Z]{3}", tif_path)
        if not tile_match:
            print(f"Warning: 无法提取Tile编号 - {tif_path}")
            continue
        tile = tile_match.group()
        if tile not in list(output_dict.keys()):
            output_dict[tile] = {}
        date_match = re.search(r"(\d{8})T", tif_path)
        if not date_match:
            print(f"Warning: 无法提取日期 - {tif_path}")
            continue
        date_str = date_match.group(1)
        file_date = datetime.datetime.strptime(date_str, "%Y%m%d").date()
        if file_date not in list(output_dict[tile].keys()):
            output_dict[tile][file_date] = [tif_path]
        else:
            output_dict[tile][file_date].append(tif_path)
            pass
    # 对output_dict进行排序
    sorted_output_dict = {}
    for itile, ivalue in output_dict.items():
        sorted_value = {}
        for idate in sorted(output_dict[itile].keys(), reverse=True):
            sorted_value[idate] = output_dict[itile][idate]
        sorted_output_dict[itile] = sorted_value
    return sorted_output_dict


@nb.njit(parallel=True)
def analysis_pixel(data):
    """
    利用 Numba 的 parallel=True 自动进行多线程并行化像元分析。
    非常适合遥感大图预测。
    """
    n_samples, cols = data.shape
    final_outputs = np.full(n_samples, 0, dtype=np.uint8)
    # 对所有样本（像素点）进行并行循环
    for i in nb.prange(n_samples):
        # for i in range(n_samples):
        # sample = data[i]
        # 逐个样本分析
        if np.sum(data[i]) == 0:
            continue
        # tmp_value = 150
        # for idx in range(cols):
        #     if sample[idx] != 150 and sample[idx] != 0:
        #         tmp_value = sample[idx]
        #         break
        # final_outputs[i] = tmp_value
        count_100 = 0
        count_101 = 0
        for val in data[i]:
            if val == 100:
                count_100 += 1
            elif val == 101:
                count_101 += 1
        precent = count_100 / (count_100 + count_101)
        if count_100 == 0 and count_101 == 0:
            final_outputs[i] = 150
        # elif count_101 > count_100:
        #     final_outputs[i] = 101
        # else:
        #     final_outputs[i] = 100

        elif precent > 0.30:
            final_outputs[i] = 100
        else:
            final_outputs[i] = 101
    return final_outputs


def merge_result(filled_files, out_dir, block_size=1000):
    """
    将所有结果生成一景逐像元分析后的最优结果
    """
    files_num = len(filled_files)
    first_ds = gdal.Open(filled_files[0])
    x_size = first_ds.RasterXSize
    y_size = first_ds.RasterYSize
    geo = first_ds.GetGeoTransform()
    prj = first_ds.GetProjection()
    first_ds = None
    # 创建输出文件
    drv = gdal.GetDriverByName("GTiff")
    out_ds = drv.Create(
        out_dir,
        x_size,
        y_size,
        1,
        gdal.GDT_Byte,
    )
    out_ds.SetProjection(prj)
    out_ds.SetGeoTransform(geo)
    out_band = out_ds.GetRasterBand(1)
    # 分块处理
    for y0 in range(0, y_size, block_size):
        # 当前块的高度（防止越界）
        rows = min(block_size, y_size - y0)
        # 加载所有文件当前块数据 into (n_files, rows, x_size)
        block_data = np.empty((files_num, rows, x_size), np.dtype(np.uint8))
        count = 0
        for fpath in filled_files:
            ds = gdal.Open(fpath)
            band = ds.GetRasterBand(1)
            arr = band.ReadAsArray(0, y0, x_size, rows)  # shape: (rows, x_size)
            block_data[count] = arr
            arr = None
            band = None
            ds = None
            count += 1
        block_data_T = np.ascontiguousarray(
            block_data.reshape(files_num, rows * x_size).T, dtype=np.float64
        )
        best_arr = analysis_pixel(block_data_T)
        block_data_T = None
        block_data = None
        # 还原为 (rows, x_size)
        class_block = best_arr.reshape(rows, x_size)
        # 写入结果（从 (0, y0) 开始）
        out_band.WriteArray(class_block, 0, y0)
        # 进度
        progress((y0 + rows) / y_size)
    out_band.FlushCache()
    out_band = None
    out_ds = None
    gc.collect()
    return None


def best_pixel_result(sorted_files, out_dir):
    """
    逐个tile分析，每个tile生成一景逐像元分析后的最优结果
    """
    tile_class_files = []
    for tile, files in sorted_files.items():
        # 获取该tile下共有多少景影像，并将路径导出
        files_path = []
        for _, file_path in files.items():
            files_path += file_path
        files_num = len(files_path)
        # 针对这个tile生成最优结果
        tile_res_path = os.path.join(out_dir, tile + ".tif")
        # 基数
        count = 0
        for ifile in files_path:
            # 打开影像, 获取基本信息
            raster_ds = gdal.Open(ifile)
            if count == 0:
                raster_prj = raster_ds.GetProjection()
                raster_geo = raster_ds.GetGeoTransform()
                x_size = raster_ds.RasterXSize
                y_size = raster_ds.RasterYSize
                # 创建空数组，用于存放该tile所有数据
                orial_data = np.empty((files_num, y_size, x_size), np.dtype(np.uint8))
            raster_band = raster_ds.GetRasterBand(1)
            raster_arr = raster_band.ReadAsArray()
            orial_data[count] = raster_arr
            count += 1
            raster_arr = None
            raster_band = None
            raster_ds = None
        # 逐个像元分析，获取最优结果
        # 为了便于numba加速，进行数组转置处理
        orial_data_T = np.ascontiguousarray(
            orial_data.reshape(files_num, y_size * x_size).T, dtype=np.float64
        )
        best_arr = analysis_pixel(orial_data_T)
        orial_data_T = None
        # 恢复原始结果
        class_res = best_arr.reshape(y_size, x_size)
        best_arr = None
        # 存储结果，返回路径
        drv = gdal.GetDriverByName("GTiff")
        class_ds = drv.Create(tile_res_path, x_size, y_size, 1, gdal.GDT_Byte)
        class_ds.SetProjection(raster_prj)
        class_ds.SetGeoTransform(raster_geo)
        class_band = class_ds.GetRasterBand(1)
        class_band.WriteArray(class_res)
        class_band = None
        class_ds = None
        tile_class_files.append(tile_res_path)
    return tile_class_files


def Extend(xs, ys, matrix, default_value):
    """
    根据滤波模板的大小，对原始影像矩阵进行外扩。
    :param xs: 滤波模板的xsize，要求为奇数
    :param ys: 滤波模板的ysize，要求为奇数
    :param matrix: 原始影像矩阵
    :return: 依据模板大小扩展后的矩阵
    """
    xs_fill = int((xs - 1) / 2)
    ys_fill = int((ys - 1) / 2)
    # 使用镜像填充
    extended_val = np.pad(
        matrix,
        ((ys_fill, ys_fill), (xs_fill, xs_fill)),
        "constant",
        constant_values=default_value,
    )
    matrix = None
    return extended_val


def gray_filtering(xs, ys, ori_xsize, ori_ysize, kernel, ext_img):
    """

    :param xs: 卷积核大小：列
    :param ys: 卷积核大小：行
    :param kernel: 卷积核
    :param ext_img: 经扩展后的影像
    :return: 滤波后的影像
    """
    # 使用切片后影像的波段书
    # 创建切片后存储矩阵
    index = np.where(kernel == 1)
    channel = kernel.size
    filtered_img = np.zeros((channel, ori_ysize, ori_xsize), dtype=np.uint8)
    ichannel = 0
    for irow in range(ys):
        for icol in range(xs):
            filtered_img[ichannel, :, :] = ext_img[
                irow : irow + ori_ysize, icol : icol + ori_xsize
            ]
            ichannel += 1
    return filtered_img[index[0], :, :]


def gray_erode(win_size, kernel, src_data):
    ysize, xsize = src_data.shape
    extend_src_data = Extend(win_size, win_size, src_data, default_value=255)
    filter_img = gray_filtering(
        int(win_size), int(win_size), xsize, ysize, kernel, extend_src_data
    )
    dst_img = np.min(filter_img, axis=0)
    filter_img = None
    return dst_img


def gray_dilate(win_size, kernel, src_data):
    ysize, xsize = src_data.shape
    extend_src_data = Extend(win_size, win_size, src_data, default_value=0)
    filter_img = gray_filtering(
        int(win_size), int(win_size), xsize, ysize, kernel, extend_src_data
    )
    dst_img = np.max(filter_img, axis=0)
    filter_img = None
    return dst_img


def opening(win_size, kernel, thr, src_data):
    """
    先腐蚀后膨胀，光滑目标轮廓，消除小目标（如去掉毛刺和孤立点），在纤细出分离物体，常用于去除小颗粒噪声以及断开目标之间的粘连
    :param win_size:
    :param kernel:
    :param fr_value:
    :param bg_value:
    :param src_data:
    :return:
    """
    for _ in range(thr):
        src_data = gray_erode(win_size, kernel, src_data)
    for _ in range(thr):
        src_data = gray_dilate(win_size, kernel, src_data)
    return src_data


def closing(win_size, kernel, thr, src_data):
    """
    先膨胀后腐蚀，能够填平小湖（即小孔），弥合小裂缝，而总的位置和形状不变
    :param win_size:
    :param kernel:
    :param fr_value:
    :param bg_value:
    :param src_data:
    :return:
    """
    for _ in range(thr):
        src_data = gray_dilate(win_size, kernel, src_data)
    for _ in range(thr):
        src_data = gray_erode(win_size, kernel, src_data)
    return src_data


def sieve(in_file, dst_dir, operate, th, op, co):
    # 定义结构元
    SE = {
        4: np.array([0, 1, 0, 1, 1, 1, 0, 1, 0]),
        8: np.array([1, 1, 1, 1, 1, 1, 1, 1, 1]),
    }
    basename = os.path.splitext(os.path.basename(in_file))[0]
    dst_file = os.path.join(dst_dir, basename) + "_sieve.tif"
    if os.path.exists(dst_file):
        return None
    in_ds = gdal.Open(in_file)
    xsize = in_ds.RasterXSize
    ysize = in_ds.RasterYSize
    prj = in_ds.GetProjection()
    geo = in_ds.GetGeoTransform()
    srcband = in_ds.GetRasterBand(1)
    # 创建输出文件，存放经开运算和填孔洞后的结果
    drv = gdal.GetDriverByName("GTiff")
    dst_ds = drv.Create(dst_file, xsize, ysize, 1, gdal.GDT_Byte)
    dst_ds.SetProjection(prj)
    dst_ds.SetGeoTransform(geo)
    dstband = dst_ds.GetRasterBand(1)
    maskband = None
    result = gdal.SieveFilter(srcband, maskband, dstband, th, co[1], callback=None)
    dstband.FlushCache()
    # 进行开操作，平滑边缘
    kernel = SE[co[1]]
    win_size = np.sqrt(kernel.size)
    src_data = dstband.ReadAsArray()
    if not win_size % 1 == 0:
        raise ("The size of SE is wrong!")
    # 根据输入判断是进行开运算还是进行闭运算
    if operate:
        filter_img = closing(win_size, kernel, op, src_data)
    else:
        filter_img = opening(win_size, kernel, op, src_data)
    # 更新结果
    dstband.WriteArray(filter_img)
    dstband.FlushCache()
    src_data = None
    dstband = None
    dst_ds = None
    in_ds = None
    filter_img = None
    return dst_file


def tif_clip(file, shp, out_dir, nodata=None):
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
            return []
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
            # progress(count / total_block)
            count += 1
        # progress(1.0)
        temp_shp_ds = None
        new_shp_l = None
        re_shp_ds = None
        raster_ds = None
    shp_ds = None
    shp_lyr = None
    return [out]


if __name__ == "__main__":
    # 确定第一次修补，第一次为0，第二次为1，依次类推
    repair_count = 0
    region = "north"
    year = "2026"
    dir_dict = {"2025": "sdb", "2026": "sdc"}
    if repair_count == 0:
        shp_dir = f"/mnt/nvme2n1/liming/xzqh_shp/{region}"
        # shp_dir = f"/mnt/nvme2n1/liming/xzqh_shp/south"
    else:
        # shp_dir = f"/mnt/nvme2n1/liming/xzqh_shp/{year}-{region}-{repair_count}"
        shp_dir = f"/mnt/sda/XJData/vector/{year}_{region}-{repair_count}"
    county_list = []
    file_list = os.listdir(shp_dir)
    for file in file_list:
        if file.endswith(".shp"):
            county_name = os.path.splitext(file)[0].split("_")[-1]
            county_list.append(county_name)
        else:
            continue
    nodata = 0

    # county_list = ["gaochangqu", "tuokexunxian", "shanshanxian"]

    for county in county_list:
        # if county in ["manasixian-1"]:
        #     continue
        print(f"开始处理{county}")
        if repair_count == 0:
            tif_dir = f"/mnt/{dir_dict[year]}/XinJiang/{year}/{region}_{year}/S2_Classification/{county}"
            # tif_dir = f"/mnt/{dir_dict[year]}/XinJiang/{year}/{region}_{year}/before0620-1/S2_Classification/{county}"
            out_dir = (
                f"/mnt/{dir_dict[year]}/XinJiang/{year}/{region}_{year}/S2_Clip_Merge_30"
                # f"/mnt/{dir_dict[year]}/XinJiang/{year}/{region}_{year}/before0620-1/S2_Clip_Merge"
            )
        else:
            tif_dir = f"/mnt/{dir_dict[year]}/XinJiang/{year}/{region}_{year}/S2_Classification-{repair_count}/{county}"
            out_dir = f"/mnt/{dir_dict[year]}/XinJiang/{year}/{region}_{year}/S2_Clip_Merge-{repair_count}"
        shp_path = searchfiles(shp_dir, partfileinfo=f"*{county}.shp")[0]
        out_path = f"{out_dir}/{year}_{region}_{county}_merge.tif"
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        if os.path.exists(out_path):
            print(f"{out_path}已存在")
        else:
            temp_dir = tempfile.mkdtemp(dir="/mnt/nvme2n1/liming/temp", prefix="MERGE_")
            # tif_list = searchfiles(tif_dir, partfileinfo=f"*_{year}07*.tif")
            tif_list = searchfiles(tif_dir, partfileinfo="*.tif")
            jobs = (
                os.cpu_count() - 1 if os.cpu_count() < len(tif_list) else len(tif_list)
            )
            pool = mp.Pool(processes=jobs)
            try:
                # 裁剪
                clip_files_result = []
                for ifile in tif_list:
                    clip_files_result.append(
                        pool.apply_async(
                            tif_clip,
                            args=(
                                ifile,
                                shp_path,
                                temp_dir,
                                nodata,
                            ),
                        )
                    )
                clip_files_path = []
                for ires in clip_files_result:
                    clip_files_path += ires.get()
                # # 利用裁剪逐个tile处理，将该tile涉及的所有影像进行排序,时间最近的在最前，逐像元分析
                # 对clip影像按照时间排序
                sorted_files_path = sorted_image(clip_files_path)
                best_result_files = best_pixel_result(sorted_files_path, temp_dir)
                # 后处理image_sieve
                # 填充孔洞大小阈值
                threshold = 5
                # 开闭运算操作次数
                open_num = 2
                # 选择进行的形态学运算opening=0, closing=1
                operate = 1
                # connectedness = [SieveFilter, opening/closing]
                connectedness = [4, 8]
                sieve_result = []
                for ifile in best_result_files:
                    sieve_result.append(
                        pool.apply_async(
                            sieve,
                            args=(
                                ifile,
                                temp_dir,
                                operate,
                                threshold,
                                open_num,
                                connectedness,
                            ),
                        )
                    )
                sieved_files = []
                for res in sieve_result:
                    sieved_files.append(res.get())
                # 将影像统一为同一投影EPSG:102025
                rpj_result = []
                for ifile in sieved_files:
                    # rpj_files += reproject_dataset(ifile, temp_dir)
                    rpj_result.append(
                        pool.apply_async(
                            reproject_dataset,
                            args=(
                                ifile,
                                temp_dir,
                            ),
                        )
                    )
                rpj_files = []
                for ires in rpj_result:
                    rpj_files += ires.get()
                # 将所有结果填充到shp限定的范围内
                fill_files_result = []
                for ifile in rpj_files:
                    # fill_files_path += class_fill(ifile, shp_path, temp_dir)
                    fill_files_result.append(
                        pool.apply_async(
                            class_fill,
                            args=(
                                ifile,
                                shp_path,
                                temp_dir,
                            ),
                        )
                    )
                fill_files_path = []
                for ires in fill_files_result:
                    fill_files_path += ires.get()
                # 将完整的结果融合
                merge_result(fill_files_path, out_path)
            finally:
                pool.close()
                pool.join()
                shutil.rmtree(temp_dir)
