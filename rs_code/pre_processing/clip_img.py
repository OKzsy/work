#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/3/29 9:30

Description:
    对栅格分要素裁剪

Parameters
    参数1：待裁剪的影像
    参数2：各个类别shapefile所在目录
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
import subprocess
try:
    from osgeo import gdal, ogr
except ImportError:
    import gdal, ogr
try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def search_dir(in_dir):

    files = os.listdir(in_dir)
    out_dir_list = []
    for file in files:
        if os.path.isdir(os.path.join(in_dir, file)):
            out_dir_list.append(os.path.join(in_dir, file))

    return out_dir_list

def search_file(folder_path, file_extension):
    search_files = []
    for dirpath, dirnames, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(file_extension):
                search_files.append(os.path.normpath(os.path.join(dirpath, file)))
    return search_files

def clip_raster(in_file, shapefile, srcnodata, dstnodata, out_file):


    # 新建缓存文件夹
    sys_str = platform.system()
    if (sys_str == 'Windows'):
        warp_path = 'gdalwarp'
    else:
        warp_path = '/usr/local/bin/gdalwarp'

    clip_cmd_str = '%s --config GDAL_FILENAME_IS_UTF8 NO --config GDALWARP_IGNORE_BAD_CUTLINE YES  -srcnodata %d -dstnodata %d' \
                   ' -q -cutline %s -crop_to_cutline -of GTiff -overwrite -wm %d -wo NUM_THREADS=ALL_CPUS -co TILED=YES %s %s' \
                   %(warp_path, srcnodata, dstnodata, shapefile, 4096, in_file, out_file)

    subprocess.call(clip_cmd_str, shell=True)


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
        # field_name = fieldDefn.GetName()
        #
        # if field_name != '_Name_':
        #     continue
        out_layer.CreateField(fieldDefn)

    # Get the output Layer's Feature Definition
    out_layerDefn = out_layer.GetLayerDefn()

    # Add features to the ouput Layer
    for ifeature in in_layer:
        # Create output Feature
        out_feature = ogr.Feature(out_layerDefn)
        # Add field values from input Layer
        for i in range(0, out_layerDefn.GetFieldCount()):
            fieldDefn = out_layerDefn.GetFieldDefn(i)
            # field_name = fieldDefn.GetName()
            # if field_name != '_Name_':
            #     continue

            # if fieldName not in field_name_target:
            #     continue
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

def main(in_file, in_dir, feature_id, out_dir):

    # 新建缓存文件夹
    rand_str = ''.join(random.sample(string.ascii_letters + string.digits, 4))
    temp_dir = os.path.join(tempfile.gettempdir(), 'gdal_%s' % rand_str)
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    os.mkdir(temp_dir)

    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    shp_list = search_file(in_dir, '.shp')

    for ishp in range(len(shp_list)):
        feature_names = get_feature_name(shp_list[ishp], feature_id)

        for ifeature in range(0, len(feature_names)):

            filter_str = "%s = '%s'" % (feature_id, feature_names[ifeature])

            ishapefile = os.path.join(temp_dir, '%s_%s.shp' % (os.path.splitext(os.path.basename(shp_list[ishp]))[0],
                                                                    feature_names[ifeature]))
            clip_shape(shp_list[ishp], filter_str, ishapefile)

            itif_file = os.path.join(out_dir, '%s_%s.tif' % (os.path.splitext(os.path.basename(in_file))[0],
                                                                    feature_names[ifeature]))
            clip_raster(in_file, ishapefile, 0, 0, itif_file)

        progress((ishp + 1) / len(shp_list))

    shutil.rmtree(temp_dir)


if __name__ == '__main__':

    start_time = time.time()

    if len(sys.argv[1:]) < 4:
        sys.exit('Problem reading input')
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])

    end_time = time.time()

    print("time: %.2f min." % ((end_time - start_time) / 60))
