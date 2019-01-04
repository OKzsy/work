#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/8/27 19:28

Description:
    对栅格分要素裁剪

Parameters
    参数1：待裁剪的影像所在目录
    参数2：各个类别shapefile文件所在路径
    参数3: shapefile字段名
    参数4：输出tif目录

"""

import os
import sys
import time
import tempfile
import shutil
import random
import string
import platform
import multiprocessing as mp
import psutil
import numpy as np
try:
    from osgeo import gdal, ogr, osr
except ImportError:
    import gdal, ogr, osr
try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


# 文件直角(笛卡尔)坐标转成文件地理坐标
def pixel2map(pixelx, pixely, in_geo):
    mapx = in_geo[0] + pixelx * in_geo[1]
    mapy = in_geo[3] + pixely * in_geo[5]
    return mapx, mapy

# 地理文件坐标转成文件直角(笛卡尔)坐标
def map2pixel(mapx, mapy, in_geo):
    pixelx = (mapx - in_geo[0]) / in_geo[1] + 0.5
    pixely = (mapy - in_geo[3]) / in_geo[5] + 0.5
    return int(pixelx), int(pixely)


def search_file(folder_path, file_extension):
    search_files = []
    for dirpath, dirnames, files in os.walk(folder_path):
        for file in files:
            if (file.lower().endswith(file_extension)):
                search_files.append(os.path.normpath(os.path.join(dirpath, file)))
    return search_files

def run_clip_raster(in_list):

    tif_files = in_list[0]
    shp_files = in_list[1]
    out_dir = in_list[2]

    shp_driver = ogr.GetDriverByName("ESRI Shapefile")

    for tif_file in tif_files:

        sds = gdal.Open(tif_file)

        if sds is None:
            continue

        xsize = sds.RasterXSize
        ysize = sds.RasterYSize
        geo = sds.GetGeoTransform()
        proj = sds.GetProjectionRef()

        sds = None

        for shp_file in shp_files:
            shp_sds = shp_driver.Open(shp_file, 0)
            mapx_min, mapx_max, mapy_min, mapy_max = shp_sds.GetLayer().GetExtent()

            shp_proj_wkt = shp_sds.GetLayer().GetSpatialRef()

            img_proj_wkt = osr.SpatialReference()
            img_proj_wkt.ImportFromWkt(proj)

            # shp2img四角坐标转换
            ct = osr.CoordinateTransformation(shp_proj_wkt, img_proj_wkt)
            top_left_mapx, top_Left_mapy, temp = ct.TransformPoint(mapx_min, mapy_max, 0)
            top_right_mapx, top_right_mapy, temp = ct.TransformPoint(mapx_max, mapy_max, 0)
            bottom_left_mapx, bottom_left_mapy, temp = ct.TransformPoint(mapx_min, mapy_min, 0)
            bottom_right_mapx, bottom_right_mapy, temp = ct.TransformPoint(mapx_max, mapy_min, 0)

            mapx_array = np.array([top_left_mapx, top_right_mapx, bottom_left_mapx, bottom_right_mapx], dtype=np.double)
            mapy_array = np.array([top_Left_mapy, top_right_mapy, bottom_left_mapy, bottom_right_mapy], dtype=np.double)

            # shp样本左上角坐标在基准影像的地理坐标
            top_left_mapx_new = np.min(mapx_array)
            top_left_mapy_new = np.max(mapy_array)

            # shp样本右下角坐标在基准影像的地理坐标
            bottom_right_mapx_new = np.max(mapx_array)
            bottom_right_mapy_new = np.min(mapy_array)

            # 样本左上角坐标在基准影像的直角坐标
            top_left_pixelx, top_Left_pixely = map2pixel(top_left_mapx_new, top_left_mapy_new, geo)
            # 样本右下角坐标在基准影像的直角坐标
            bottom_right_pixelx, bottom_right_pixely = map2pixel(bottom_right_mapx_new, bottom_right_mapy_new, geo)

            # if (np.min(np.array([top_left_pixelx, top_Left_pixely, bottom_right_pixelx, bottom_right_pixely])) < 0) or\
            #         (np.min([top_left_pixelx, bottom_right_pixelx]) > xsize) or (np.min([top_Left_pixely, bottom_right_pixely]) > ysize):


            if (top_left_pixelx < 0) or (top_Left_pixely < 0) or (bottom_right_pixelx > xsize) or (bottom_right_pixely > ysize):
                shp_sds = None
                continue


            out_file = os.path.join(out_dir, '%s_%s.tif' % (os.path.splitext(os.path.basename(tif_file))[0],
                                                            os.path.splitext(os.path.basename(shp_file))[0]))
            try:
                clip_raster(tif_file, shp_file, 0, 0, out_file)
            except:
                print('%s shp problem' % os.path.basename(shp_file))
                continue

            out_sds = gdal.Open(out_file)

            if np.max(out_sds.ReadAsArray()) <= 0:
                out_sds = None
                os.remove(out_file)
            # bottom_right_pixelx = top_left_pixelx + sample_xsize
            # bottom_right_pixely = top_Left_pixely + sample_ysize


def clip_raster(in_file, shapefile, srcnodata, dstnodata, out_file):


    # 单位为字节
    gdal.SetConfigOption('GDALWARP_IGNORE_BAD_CUTLINE', 'YES')
    gdal.PushErrorHandler('CPLQuietErrorHandler')

    tiff_driver = gdal.GetDriverByName("GTiff")
    if os.path.exists(out_file):
        tiff_driver.Delete(out_file)

    gdal.Warp(out_file, in_file, cutlineDSName=shapefile, cropToCutline=True,
              srcNodata=srcnodata, dstNodata=dstnodata, multithread=True)


def clip_shape(in_shape, filter_str, out_shape):

    gdal.SetConfigOption('SHAPE_ENCODING', 'GBK')

    # Get the input Layer
    shp_driver = ogr.GetDriverByName("ESRI Shapefile")
    in_source = shp_driver.Open(in_shape, 0)
    in_layer = in_source.GetLayer()
    spatialRef = in_layer.GetSpatialRef()

    in_layer.SetAttributeFilter(filter_str)

    # Remove output shapefile if it already exists
    if os.path.exists(out_shape):
        shp_driver.DeleteDataSource(out_shape)

    # Create the output shapefile
    out_source = shp_driver.CreateDataSource(out_shape)

    out_lyr_name = os.path.splitext(os.path.split(out_shape)[1])[0]
    out_layer = out_source.CreateLayer(out_lyr_name, geom_type = ogr.wkbMultiPolygon, srs = spatialRef)

    # Add all input Layer Fields to the output Layer
    in_layerDefn = in_layer.GetLayerDefn()
    for i in range(0, in_layerDefn.GetFieldCount()):
        fieldDefn = in_layerDefn.GetFieldDefn(i)
        out_layer.CreateField(fieldDefn)

    # Get the output Layer's Feature Definition
    out_layerDefn = out_layer.GetLayerDefn()

    # Add features to the ouput Layer
    for ifeature in in_layer:
        # Create output Feature
        out_feature = ogr.Feature(out_layerDefn)
        # Add field values from input Layer
        for i in range(0, out_layerDefn.GetFieldCount()):
            out_feature.SetField(out_layerDefn.GetFieldDefn(i).GetNameRef(),
                                ifeature.GetField(i))

        # Set geometry as centroid
        geom = ifeature.GetGeometryRef()
        out_feature.SetGeometry(geom.Clone())
        # Add new feature to output Layer
        out_layer.CreateFeature(out_feature)
        out_feature = None

    # Save and close DataSources
    in_source = None
    out_source = None


def get_feature_name(shapefile, feature_id):

    gdal.SetConfigOption('SHAPE_ENCODING', 'GBK')

    # print(temp_dir)

    # search feature name
    shp_driver = ogr.GetDriverByName('ESRI Shapefile')
    in_source = shp_driver.Open(shapefile, 0)

    if in_source is None:
        sys.exit('Problem opening file %s !' % shapefile)
    in_layer = in_source.GetLayer()
    num_feature = in_layer.GetFeatureCount()

    # feature_names = []
    feature_names = []

    for i in range(0, num_feature):
        feature = in_layer.GetFeature(i)
        # feature_name = feature.GetField("Name")
        feature_name = feature.GetField('%s' %(feature_id))
        # feature_names.append(feature_name)
        feature_names.append(feature_name)
    in_source = None

    return feature_names

def main(in_dir, in_shp, feature_id, out_shp_dir, out_tif_dir):

    if not os.path.exists(out_shp_dir):
        os.mkdir(out_shp_dir)

    if not os.path.exists(out_tif_dir):
        os.mkdir(out_tif_dir)

    feature_names = get_feature_name(in_shp, feature_id)
    shp_files = []
    for ifeature in range(0, len(feature_names)):
        filter_str = "%s = '%s'" % (feature_id, feature_names[ifeature])
        ishapefile = os.path.join(out_shp_dir, '%s_%s.shp' % (os.path.splitext(os.path.basename(in_shp))[0],
                                                           feature_names[ifeature]))

        if os.path.exists(ishapefile):
            shp_files.append(ishapefile)
            continue

        try:
            clip_shape(in_shp, filter_str, ishapefile)
        except:
            shp_driver = ogr.GetDriverByName("ESRI Shapefile")
            if os.path.exists(ishapefile):
                shp_driver.DeleteDataSource(ishapefile)
            print(feature_names[ifeature])
            continue
        shp_files.append(ishapefile)

    tif_files = search_file(in_dir, '.tif')
    if shp_files == []:
        sys.exit('no shapefile')
    # run_clip_raster([tif_files, shp_files])
    # 建立进程池
    sys_str = platform.system()
    if (sys_str == 'Windows'):
        num_proc = int(mp.cpu_count())
    else:
        num_proc = int(mp.cpu_count() - 1)

    if len(tif_files) < num_proc:
        num_proc = len(tif_files)
        block_num_file = 1
    else:
        block_num_file = int(len(tif_files) / num_proc)

    result_list = []

    pool = mp.Pool(processes=num_proc)

    for iproc in range(num_proc):

        if iproc == (num_proc - 1):
            sub_in_files = tif_files[(iproc * block_num_file):]
        else:
            sub_in_files = tif_files[(iproc * block_num_file): (iproc * block_num_file) + block_num_file]

        in_list = [sub_in_files, shp_files, out_tif_dir]

        result = pool.apply_async(run_clip_raster, args=(in_list,))
        result_list.append(result)

        progress(0.25 + iproc / num_proc * 0.65)

    for r in result_list:
        print(r.get())

    pool.close()
    pool.join()

    progress(1)


if __name__ == '__main__':

    start_time = time.time()

    if len(sys.argv[1:]) < 4:
        sys.exit('Problem reading input')


    in_dir = sys.argv[1]
    shp_file = sys.argv[2]
    out_shp_dir = sys.argv[3]
    out_tif_dir = sys.argv[4]

    # in_dir = r'D:\Data\Test_data\clip\20181021_zhongmu_dapeng\in_tif'
    # shp_file = r"D:\Data\Test_data\clip\20181021_zhongmu_dapeng\hansi_guandu_qita\hansizhen_qita.shp"
    # out_shp_dir = r"D:\Data\Test_data\clip\20181021_zhongmu_dapeng\out_shp"
    # out_tif_dir = r"D:\Data\Test_data\clip\20181021_zhongmu_dapeng\out_tif"


    # in_dir = r'D:\Data\Test_data\classification\yancao_20181115\in_dir'
    # shp_file = r"D:\Data\Test_data\classification\yancao_20181115\伊川\yichuan_sample.shp"
    # out_shp_dir = r'D:\Data\Test_data\classification\yancao_20181115\out_shp_dir'
    # out_tif_dir = r'D:\Data\Test_data\classification\yancao_20181115\out_tif_dir'

    main(in_dir, shp_file, 'Name', out_shp_dir, out_tif_dir)

    end_time = time.time()

    print("time: %.2f min." % ((end_time - start_time) / 60))