#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/8/27 19:28

Description:
    对栅格分要素裁剪

Parameters
    参数1：待裁剪的影像所在目录或者文件路径
    参数2：各个类别shapefile文件所在路径
    参数3: shapefile字段名
    参数4：输出tif目录

"""

import os
import sys
import time
import multiprocessing as mp
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
# 切片字典
def dict_slice(adict, start, end):
    keys = list(adict.keys())
    dict_slice = {}
    for k in keys[start:end]:
        dict_slice[k] = adict[k]
    return dict_slice

def search_file(folder_path, file_extension):
    search_files = []
    for dirpath, dirnames, files in os.walk(folder_path):
        for file in files:
            if (file.lower().endswith(file_extension)):
                search_files.append(os.path.normpath(os.path.join(dirpath, file)))
    return search_files

def clip_img(in_list):

    in_file = in_list[0]
    shp_files = in_list[1]
    tif_dir = in_list[2]
    shp_driver = ogr.GetDriverByName("ESRI Shapefile")
    sds = gdal.Open(in_file)
    xsize = sds.RasterXSize
    ysize = sds.RasterYSize
    geo = sds.GetGeoTransform()
    proj = sds.GetProjectionRef()
    sds = None

    for ishp in range(len(shp_files)):
        shp_sds = shp_driver.Open(shp_files[ishp], 0)
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


        if (top_left_pixelx < 0) or (top_Left_pixely < 0) or (bottom_right_pixelx > xsize) or (
                bottom_right_pixely > ysize):
            shp_sds = None
            continue

        out_file = os.path.join(tif_dir, '%s_%s.tif' % (os.path.splitext(os.path.basename(in_file))[0],
                                                        os.path.splitext(os.path.basename(shp_files[ishp]))[0]))
        try:
            gdal.SetConfigOption('GDALWARP_IGNORE_BAD_CUTLINE', 'YES')
            gdal.PushErrorHandler('CPLQuietErrorHandler')
            gdal.Warp(out_file, in_file, cutlineDSName=shp_files[ishp], cropToCutline=True,
                      srcNodata=0, dstNodata=0)
        except:
            print('%s shp problem' % os.path.basename(shp_file))
            continue

        out_sds = gdal.Open(out_file)
        if out_sds == None:
            continue
        if np.max(out_sds.ReadAsArray()) <= 0:
            out_sds = None
            os.remove(out_file)
            continue

        progress((ishp+1) / len(shp_files))
    # progress(1)



def clip_shape(in_list):

    in_shape = in_list[0]
    feature_dict = in_list[1]
    out_shp_dir = in_list[2]

    gdal.SetConfigOption('SHAPE_ENCODING', 'GBK')

    # Get the input Layer
    shp_driver = ogr.GetDriverByName("ESRI Shapefile")
    in_source = shp_driver.Open(in_shape, 0)
    in_layer = in_source.GetLayer()
    spatialRef = in_layer.GetSpatialRef()

    # Add all input Layer Fields to the output Layer
    in_layerDefn = in_layer.GetLayerDefn()

    fid_list = list(feature_dict.keys())
    out_shps = []
    for ifid in range(len(fid_list)):

        out_shape = os.path.join(out_shp_dir, '%s_%s.shp' % (os.path.splitext(os.path.basename(in_shape))[0],
                                                             feature_dict[fid_list[ifid]]))
        if os.path.exists(out_shape):
            out_shps.append(out_shape)
            continue

        in_feature = in_layer.GetFeature(fid_list[ifid])
        # Create the output shapefile
        out_source = shp_driver.CreateDataSource(out_shape)

        out_lyr_name = os.path.splitext(os.path.split(out_shape)[1])[0]
        out_layer = out_source.CreateLayer(out_lyr_name, geom_type=ogr.wkbMultiPolygon, srs=spatialRef)
        # Add all input Layer Fields to the output Layer
        for i in range(0, in_layerDefn.GetFieldCount()):
            fieldDefn = in_layerDefn.GetFieldDefn(i)
            out_layer.CreateField(fieldDefn)

        # Get the output Layer's Feature Definition
        out_layerDefn = out_layer.GetLayerDefn()

        out_feature = ogr.Feature(out_layerDefn)
        # Add field values from input Layer
        for i in range(0, out_layerDefn.GetFieldCount()):
            out_feature.SetField(out_layerDefn.GetFieldDefn(i).GetNameRef(),
                                 in_feature.GetField(i))

        # Set geometry as centroid
        geom = in_feature.GetGeometryRef()
        out_feature.SetGeometry(geom.Clone())
        # Add new feature to output Layer
        out_layer.CreateFeature(out_feature)
        out_feature = None
        out_layer = None
        out_source = None
        out_shps.append(out_shape)

        progress((ifid + 1) / len(fid_list))

    # Save and close DataSources
    in_source = None
    # progress(1)

    return out_shps

def get_feature_dict(shapefile, feature_id):

    gdal.SetConfigOption('SHAPE_ENCODING', 'GBK')

    # search feature name
    shp_driver = ogr.GetDriverByName('ESRI Shapefile')
    in_source = shp_driver.Open(shapefile, 0)

    if in_source is None:
        sys.exit('Problem opening file %s !' % shapefile)
    in_layer = in_source.GetLayer()
    num_feature = in_layer.GetFeatureCount()

    # feature_names = []
    feature_dict = {}

    for i in range(0, num_feature):
        feature = in_layer.GetFeature(i)
        # feature.SetField(class_id, 233)
        feature_name = feature.GetField('%s' % (feature_id))
        # feature_names.append(feature_name)
        feature_dict[i] = feature_name

    in_source.Destroy()
    in_layer = None

    return feature_dict

def multi_clip_shp(in_shp, feature_dict, shp_dir):

    num_proc = int(mp.cpu_count() - 1)

    if len(feature_dict) < num_proc:
        num_proc = len(feature_dict)
        block_num_file = 1
    else:
        block_num_file = int(len(feature_dict) / num_proc)

    pool = mp.Pool(processes=num_proc)

    results = []
    for iproc in range(num_proc):

        if iproc == (num_proc - 1):
            sub_in_files = dict_slice(feature_dict, iproc * block_num_file, len(feature_dict))
        else:
            sub_in_files = dict_slice(feature_dict, iproc * block_num_file, iproc * block_num_file + block_num_file)

        # print(len(sub_in_files))

        in_list = [in_shp, sub_in_files, shp_dir]

        results.append(pool.apply_async(clip_shape, args=(in_list,)))

        # progress(iproc / num_proc)

    pool.close()
    pool.join()
    shp_files = []
    for r in results:
        shp_files = shp_files + r.get()

    return shp_files

def multi_clip_img(in_file, shp_files, tif_dir):

    num_proc = int(mp.cpu_count() - 1)

    if len(shp_files) < num_proc:
        num_proc = len(shp_files)
        block_num_file = 1
    else:
        block_num_file = int(len(shp_files) / num_proc)

    pool = mp.Pool(processes=num_proc)

    results = []
    for iproc in range(num_proc):

        if iproc == (num_proc - 1):
            sub_in_files = shp_files[(iproc * block_num_file):]
        else:
            sub_in_files = shp_files[(iproc * block_num_file): (iproc * block_num_file) + block_num_file]

        # print(len(sub_in_files))

        in_list = [in_file, sub_in_files, tif_dir]

        results.append(pool.apply_async(clip_img, args=(in_list,)))

        # progress(iproc / num_proc)

    pool.close()
    pool.join()

    for r in results:
        r.get()



def main(in_dir, in_shp, feature_id, out_shp_dir, out_tif_dir):

    if not os.path.exists(out_shp_dir):
        os.mkdir(out_shp_dir)

    if not os.path.exists(out_tif_dir):
        os.mkdir(out_tif_dir)

    feature_dict = get_feature_dict(in_shp, feature_id)
    print('multiprocessing clip shp start...')
    shp_files = multi_clip_shp(in_shp, feature_dict, out_shp_dir)
    print('multiprocessing clip shp done.')

    print('multiprocessing clip img start...')


    if os.path.isdir(in_dir):
        in_files = search_file(in_dir, '.tif')
    else:
        in_files = [in_dir]

    for in_file in in_files:
        multi_clip_img(in_file, shp_files, out_tif_dir)

    print('multiprocessing clip img done.')
    print('all done')

if __name__ == '__main__':

    start_time = time.time()

    if len(sys.argv[1:]) < 4:
        sys.exit('Problem reading input')


    in_dir = sys.argv[1]
    shp_file = sys.argv[2]
    out_shp_dir = sys.argv[3]
    out_tif_dir = sys.argv[4]

    # in_dir = r'\\192.168.0.234\nydsj\project\9.Insurance_gongyi\2.data\planet\3.clip\20180903_20181015_20181026'
    # shp_file = r"\\192.168.0.234\nydsj\project\5.zhengzhou_cailanzi\1.sample\2.shp\4.DL\gongyi\land_gongyi_GF2.shp"
    # out_shp_dir = r"\\192.168.0.234\nydsj\user\TJG\classification\20181221\out_shp"
    # out_tif_dir = r"\\192.168.0.234\nydsj\user\TJG\classification\20181221\out_tif"

    main(in_dir, shp_file, 'Name', out_shp_dir, out_tif_dir)

    end_time = time.time()

    print("time: %.2f min." % ((end_time - start_time) / 60))