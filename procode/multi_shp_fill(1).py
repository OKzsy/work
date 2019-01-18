#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/12/6 10:51

Description:


Parameters


"""

import os
import sys
import csv
import time
import random
import string
import tempfile
import shutil
import psutil
import numpy as np
import numexpr as ne
import pandas as pd
import subprocess
import platform
from collections import Counter
from scipy import stats
import multiprocessing as mp
try:
    from osgeo import gdal, ogr
except ImportError:
    import gdal, ogr

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def read_csv(in_file):

    with open(in_file, 'r') as in_func:
        flag_str = in_func.readlines()
    flag_dict = {}
    for iflag_str in flag_str:
        iflag_data = iflag_str.replace('\n', '').split(',')

        while '' in iflag_data:
            iflag_data.remove('')
        flag_dict[int(iflag_data[0])] = iflag_data[1:]

    sort_dict = {}

    key_list =  list(sorted(flag_dict.keys()))
    for ikey in key_list:
        sort_dict[ikey] = flag_dict[ikey]

    return sort_dict
def dict_slice(adict, start, end):
    keys = list(adict.keys())
    dict_slice = {}
    for k in keys[start:end]:
        dict_slice[k] = adict[k]
    return dict_slice

def get_flag(flag_file):
    with open(flag_file, 'r') as in_func:
        flag_str = in_func.readlines()

    flag_dict = {}

    for iflag_str in flag_str:
        iflag_data = iflag_str.replace('\n', '').split(',')

        while '' in iflag_data:
            iflag_data.remove('')

        flag_dict[int(iflag_data[1])] = iflag_data[0]

    return flag_dict


def update_shape(in_shape, class_pre_dict, out_shape):

    gdal.SetConfigOption('SHAPE_ENCODING', 'GBK')

    # Get the input Layer
    shp_driver = ogr.GetDriverByName("ESRI Shapefile")
    in_source = shp_driver.Open(in_shape, 0)
    in_layer = in_source.GetLayer()
    spatialRef = in_layer.GetSpatialRef()
    num_feature = in_layer.GetFeatureCount()

    # Remove output shapefile if it already exists
    if os.path.exists(out_shape):
        shp_driver.DeleteDataSource(out_shape)

    # Create the output shapefile
    out_source = shp_driver.CreateDataSource(out_shape)
    out_lyr_name = os.path.splitext(os.path.split(out_shape)[1])[0]
    out_layer = out_source.CreateLayer(out_lyr_name, geom_type=ogr.wkbMultiPolygon, srs=spatialRef)

    # Add all input Layer Fields to the output Layer
    in_layerDefn = in_layer.GetLayerDefn()
    for i in range(0, in_layerDefn.GetFieldCount()):
        fieldDefn = in_layerDefn.GetFieldDefn(i)
        out_layer.CreateField(fieldDefn)

    field_type = ogr.OFTReal
    class_field = ogr.FieldDefn('class', ogr.OFTString)
    precent_field = ogr.FieldDefn('precent', ogr.OFTString)
    out_layer.CreateField(class_field)
    out_layer.CreateField(precent_field)

    # Get the output Layer's Feature Definition
    out_layerDefn = out_layer.GetLayerDefn()

    # Add features to the ouput Layer
    for i in range(0, num_feature):

        iclass_pre_list = class_pre_dict[i]
        # Create output Feature
        feature = in_layer.GetFeature(i)
        out_feature = ogr.Feature(out_layerDefn)
        # Add field values from input Layer
        for i in range(0, in_layerDefn.GetFieldCount()):
            out_feature.SetField(out_layerDefn.GetFieldDefn(i).GetNameRef(),
                                 feature.GetField(i))
        out_feature.SetField('class', iclass_pre_list[1])
        out_feature.SetField('precent', iclass_pre_list[2])
        # Set geometry as centroid
        geom = feature.GetGeometryRef()
        out_feature.SetGeometry(geom.Clone())
        # Add new feature to output Layer
        out_layer.CreateFeature(out_feature)
        out_feature = None
        feature = None

    # Save and close DataSources
    in_source = None
    out_source = None


def get_shp_feature_name(shapefile):

    gdal.SetConfigOption('SHAPE_ENCODING', 'GBK')

    # search feature name
    shp_driver = ogr.GetDriverByName('ESRI Shapefile')
    in_source = shp_driver.Open(shapefile, 0)

    if in_source is None:
        sys.exit('Problem opening file %s !' % shapefile)
    in_layer = in_source.GetLayer()
    num_feature = in_layer.GetFeatureCount()

    # feature_names = []
    feature_names = {}

    for i in range(0, num_feature):
        feature = in_layer.GetFeature(i)
        # feature.SetField(class_id, 233)
        feature_name = feature.GetField('%s' % ('DKBM'))
        # feature_names.append(feature_name)
        feature_names[i] = feature_name

    in_source.Destroy()
    in_layer = None

    return feature_names


def clip(in_file, out_file, shapefile, feature_id):

    gdal.SetConfigOption('GDALWARP_IGNORE_BAD_CUTLINE', 'YES')
    gdal.PushErrorHandler('CPLQuietErrorHandler')
    tiff_driver = gdal.GetDriverByName("GTiff")
    if os.path.exists(out_file):
        tiff_driver.Delete(out_file)

    gdal.Warp(out_file, in_file, cutlineDSName=shapefile, cropToCutline=True,
              srcNodata=240, dstNodata=240, cutlineWhere="%s = '%s'" % ("DKBM", feature_id))


def resampling(in_file, out_file):
    source_dataset = gdal.Open(in_file)
    if source_dataset is None:
        sys.exit('Problem opening file %s !' % in_file)

    # 获取数据基本信息
    xsize = source_dataset.RasterXSize
    ysize = source_dataset.RasterYSize
    num_band = source_dataset.RasterCount
    data_type = source_dataset.GetRasterBand(1).DataType

    geoTransform = source_dataset.GetGeoTransform()
    projection = source_dataset.GetProjectionRef()

    # output geotiff file
    out_driver = gdal.GetDriverByName('GTiff')
    if os.path.exists(out_file):
        out_driver.Delete(out_file)

    gdal.Warp(out_file, in_file, format='GTiff',
              srcNodata=200, dstNodata=200, multithread=True,
              resampleAlg=gdal.GRA_NearestNeighbour,
              xRes=0.00001, yRes=0.00001)

def get_class(in_list):
    temp_dir = in_list[0]
    resamp_file = in_list[1]
    shp_file = in_list[2]
    flag_dict = in_list[3]
    feature_names = in_list[4]
    out_csv_file = in_list[5]

    feature_names_key = list(feature_names.keys())

    out_csv = open(out_csv_file, 'w', newline='')
    out_csv_writer = csv.writer(out_csv)
    class_pre_list = []
    for ifeature in range(0, len(feature_names_key)):
        ifeature_name = str(feature_names[feature_names_key[ifeature]])
        out_file = os.path.join(temp_dir, '%s_%s.tif' % ((os.path.splitext(os.path.basename(resamp_file)))[0],
                                                         ifeature_name))
        try:
            clip(resamp_file, out_file, shp_file, ifeature_name)
        except:
            out_csv_writer.writerow([feature_names_key[ifeature], ifeature_name, 'yichang', '%.2f' % 0.0])
            continue

        if not os.path.exists(out_file):
            class_pre_list.append([feature_names_key[ifeature], ifeature_name, 'yichang', '%.2f' % 0.0])
            out_csv_writer.writerow([feature_names_key[ifeature], ifeature_name, 'yichang', '%.2f' % 0.0])
            continue
        try:
            sds = gdal.Open(out_file)
        except:
            class_pre_list.append([feature_names_key[ifeature], ifeature_name, 'yichang', '%.2f' % 0.0])
            out_csv_writer.writerow([feature_names_key[ifeature], ifeature_name, 'yichang', '%.2f' % 0.0])
            continue

        if sds is None:
            class_pre_list.append([feature_names_key[ifeature], ifeature_name, 'yichang', '%.2f' % 0.0])
            out_csv_writer.writerow([feature_names_key[ifeature], ifeature_name, 'yichang', '%.2f' % 0.0])
            # feature.SetField('class', 'yichang')
            # feature.SetField('percent', '%.2f' % 0.0)
            continue
        data = sds.ReadAsArray()

        if len(data[data != 240]) == 0:
            out_csv_writer.writerow([feature_names_key[ifeature], ifeature_name, 'yichang', '%.2f' % 0.0])
        else:
            real_data = data[np.where(data != 240)]
            fill_value = stats.mode(real_data)[0][0]
            class_str = str(flag_dict[fill_value])

            precent_value = 1.0 * len(real_data[np.where(real_data == fill_value)]) / len(real_data) * 100

            class_pre_list.append([feature_names_key[ifeature], ifeature_name, class_str, '%.2f' % precent_value])
            out_csv_writer.writerow([feature_names_key[ifeature], ifeature_name, class_str, '%.2f' % precent_value])

        progress((ifeature + 1) / len(feature_names_key))

        data = None
    out_csv.close()
    out_csv_writer = None


def main(in_file, shp_file, flag_file, out_shp_file):

    # 新建缓存文件夹
    sys_str = platform.system()
    if (sys_str == 'Windows'):
        temp_dir = os.path.join(tempfile.gettempdir(), 'gdal_temp2')
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.mkdir(temp_dir)
    else:
        rand_str = ''.join(random.sample(string.ascii_letters + string.digits, 4))
        temp_dir = os.path.join(r'/data6', 'gdal_%s' % rand_str)
        if not os.path.exists(temp_dir):
            os.mkdir(temp_dir)

    csv_dir = os.path.join(temp_dir, 'out_csv')
    if os.path.exists(csv_dir):
        shutil.rmtree(csv_dir)
    os.mkdir(csv_dir)

    #
    print('resampling start...')
    resamp_file = os.path.join(temp_dir, '%s_reseam.tif' % (os.path.splitext(os.path.basename(in_file)))[0])
    # 重采样成0.00001°(1m)
    resampling(in_file, resamp_file)

    print('resampling done')
    # 获取flag标签
    flag_dict = get_flag(flag_file)

    # 填充值
    flag_dict[200] = 'beijing'
    # 获取feature name
    print('get feature name start...')
    feature_names = get_shp_feature_name(shp_file)
    print('get feature name done')
    num_feature = len(feature_names)

    key_list = list(feature_names.keys())
    print('multiprocessing start...')
    if (platform.system() == 'Windows'):
        num_proc = int(mp.cpu_count() - 1)
    else:
        num_proc = int(mp.cpu_count() - 1)
    if len(feature_names) < num_proc:
        num_proc = len(feature_names)
        block_num_file = 1
    else:
        block_num_file = int(len(feature_names) / num_proc)

    pool = mp.Pool(processes=num_proc)
    for iproc in range(num_proc):

        if iproc == (num_proc - 1):
            sub_in_files = dict_slice(feature_names, iproc * block_num_file, num_feature)
        else:
            sub_in_files = dict_slice(feature_names, iproc * block_num_file, iproc * block_num_file + block_num_file)

        out_csv_file = os.path.join(csv_dir, 'proc%d.csv' % iproc)
        # print(len(sub_in_files))

        in_list = [temp_dir, resamp_file, shp_file, flag_dict, sub_in_files, out_csv_file]

        pool.apply_async(get_class, args=(in_list,))

        # progress(iproc / num_proc)

    pool.close()
    pool.join()
    out_file = os.path.join(temp_dir, 'all_csv.csv')
    if (platform.system() == 'Windows'):

        cmd_str = r'copy /b *.csv %s' % (out_file)
        # 不打印列表
        subprocess.call(cmd_str, shell=True, stdout=open(os.devnull, 'w'), cwd=csv_dir)

    elif (platform.system() == 'Linux'):
        cmd_str = r'cat *.csv > %s' % (out_file)
        # 不打印列表
        subprocess.call(cmd_str, shell=True, stdout=open(os.devnull, 'w'), cwd=csv_dir)
    else:
        print('no system platform')

    print('multiprocessing done...')
    print('update shapefile start...')
    update_shape(shp_file, read_csv(out_file), out_shp_file)
    print('update shapefile done...')
    shutil.rmtree(temp_dir)

    print('all done')


if __name__ == '__main__':
    start_time = time.time()

    if len(sys.argv[1:]) < 4:
        sys.exit('Problem reading input')

    # in_file = r"D:\Data\Test_data\classification\20181206\test2\planet_12band_gongyi_big_class3_copy.tif"
    # shp_file = r"D:\Data\Test_data\classification\20181206\test2\dk - 副本.shp"
    # out_shp_file = r"D:\Data\Test_data\classification\20181206\test2\dk_out_3.shp"
    # flag_file = r"D:\Data\Test_data\classification\20181206\flag3.csv"

    # shp_file = r"D:\Data\Test_data\classification\20181206\test2\dk_2.shp"
    # out_shp_file = r"D:\Data\Test_data\classification\20181206\test2\dk_2_1.shp"
    # in_file = r"D:\Data\Test_data\classification\20181206\test2\planet_12band_gongyi_dk2.tif"
    #
    # in_file = r"D:\Data\Test_data\classification\20181206\test\class.tif"
    # shp_file = r"D:\Data\Test_data\classification\20181206\test\dk - 副本.shp"
    # out_shp_file = r"D:\Data\Test_data\classification\20181206\test\dk_copy_1.shp"

    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    # main(in_file, shp_file, flag_file, out_shp_file)

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))