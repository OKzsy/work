#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/7/16 9:54

Description:
    根据输入的4通道表观反射率影响，进行云检测处理，输出云shapefile文件

Parameters
    in_file:表观反射率影响路径
    out_shapefile:输出云shp文件路径

"""

import os
import sys
import time
import tempfile
import shutil
import numpy as np
import numexpr as ne
import pandas as pd

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

def reproject_shape(in_file, out_file):

    # gdal.SetConfigOption("SHAPE_ENCODING", "GBK")

    shp_driver = ogr.GetDriverByName('ESRI Shapefile')

    out_srs = osr.SpatialReference()
    out_srs.ImportFromEPSG(4326)

    in_dataset = shp_driver.Open(in_file, 0)
    in_layer = in_dataset.GetLayer()

    in_spatialRef = in_layer.GetSpatialRef()

    # create the CoordinateTransformation
    coordTrans = osr.CoordinateTransformation(in_spatialRef, out_srs)

    # create the output layer
    if os.path.exists(out_file):
        shp_driver.DeleteDataSource(out_file)
    out_dataset = shp_driver.CreateDataSource(out_file)
    out_layer = out_dataset.CreateLayer("out", geom_type=ogr.wkbMultiPolygon, srs=out_srs)

    # add fields
    in_layerDefn = in_layer.GetLayerDefn()
    for i in range(0, in_layerDefn.GetFieldCount()):
        field_Defn = in_layerDefn.GetFieldDefn(i)
        out_layer.CreateField(field_Defn)

    # get the output layer's feature definition
    out_layerDefn = out_layer.GetLayerDefn()

    # loop through the input features
    in_feature = in_layer.GetNextFeature()
    while in_feature:
        # get the input geometry
        geom = in_feature.GetGeometryRef()
        # reproject the geometry
        geom.Transform(coordTrans)
        # create a new feature
        out_feature = ogr.Feature(out_layerDefn)
        # set the geometry and attribute
        out_feature.SetGeometry(geom)
        for i in range(0, out_layerDefn.GetFieldCount()):
            out_feature.SetField(out_layerDefn.GetFieldDefn(i).GetNameRef(), in_feature.GetField(i))
        # add the feature to the shapefile
        out_layer.CreateFeature(out_feature)
        # dereference the features and get the next input feature
        out_feature = None
        in_feature = in_layer.GetNextFeature()

    # Save and close the shapefiles
    in_dataset = None
    out_dataset = None

    # 进度条
    progress(1)


def raster2shp(temp_dir, raster_file):

    shp_file = os.path.join(temp_dir, '%s_cloud.shp' %(os.path.basename(raster_file).split('.')[0]))

    source_dataset = gdal.Open(raster_file)
    if source_dataset is None:
        sys.exit('Problem opening file %s !' % raster_file)

    xsize = source_dataset.RasterXSize
    ysize = source_dataset.RasterYSize
    band = source_dataset.GetRasterBand(1)
    geotransform = source_dataset.GetGeoTransform()
    projection = source_dataset.GetProjectionRef()
    data_type = band.DataType

    tiff_driver = gdal.GetDriverByName('GTiff')

    # create the output layer
    shp_driver = ogr.GetDriverByName("ESRI Shapefile")

    if os.path.exists(shp_file):
        shp_driver.DeleteDataSource(shp_file)

    geom_type = ogr.wkbMultiPolygon
    srs = osr.SpatialReference()
    srs.ImportFromWkt(projection)

    out_ds = shp_driver.CreateDataSource(shp_file)
    out_layer = out_ds.CreateLayer('out', geom_type=geom_type, srs=srs)


    num_xblock = 5000

    for x_offset in range(0, xsize, num_xblock):
        if x_offset + num_xblock < xsize:
            num_x = num_xblock
        else:
            num_x = xsize - x_offset

        up_left_geo = pixel2map(x_offset, 0, geotransform)
        out_geo = (up_left_geo[0], geotransform[1], 0, up_left_geo[1], 0, geotransform[5])

        # print(get_basename(raster_file)[0])

        tile_file = os.path.join(temp_dir, '%s_%d_%d.tif' % (os.path.basename(raster_file).split('.')[0],
                                                                  x_offset, num_x))

        if os.path.exists(tile_file):
            tiff_driver.Delete(tile_file)

        tile_source_dataset = tiff_driver.Create(tile_file, num_x, ysize, 1, data_type)

        tile_source_dataset.SetProjection(projection)
        tile_source_dataset.SetGeoTransform(out_geo)
        tile_band = tile_source_dataset.GetRasterBand(1)

        data = band.ReadAsArray(x_offset, 0, num_x, ysize)
        tile_band.WriteArray(data, 0, 0)
        tile_band.SetNoDataValue(0)

        tile_shapefile = os.path.join(temp_dir, '%s_%d_%d.shp' %(os.path.basename(raster_file).split('.')[0],
                                                                  x_offset, num_x))

        # print(os.path.exists(tile_shapefile))

        if os.path.exists(tile_shapefile):
            shp_driver.DeleteDataSource(tile_shapefile)

        tile_shp_dataset = shp_driver.CreateDataSource(tile_shapefile)

        # tile_out_layer = tile_shp_dataset.CreateLayer('layer',geom_type=geom_type, srs=srs)
        tile_out_layer = tile_shp_dataset.CreateLayer('layer', geom_type=geom_type, srs=srs)

        dst_fieldname = 'DN'
        fd = ogr.FieldDefn(dst_fieldname, ogr.OFTInteger)
        tile_out_layer.CreateField( fd )
        dst_field = 0
        gdal.Polygonize(tile_band, tile_band, tile_out_layer, dst_field)
        tile_source_dataset = None

        for feat in tile_out_layer:
            out_feat = ogr.Feature(out_layer.GetLayerDefn())
            out_feat.SetGeometry(feat.GetGeometryRef().Clone())
            out_layer.CreateFeature(out_feat)
            out_feat = None
            out_layer.SyncToDisk()

        tile_shp_dataset = None


        # 进度条
        # print(int((x_offset + 1) / xsize * 80))
        progress((x_offset + 1) / xsize * 0.8)
    out_ds = None

    return shp_file

def sieve_filter(in_file):

    source_dataset = gdal.Open(in_file)
    if source_dataset is None:
        sys.exit('Problem opening file %s !' % in_file)

    xsize = source_dataset.RasterXSize
    ysize = source_dataset.RasterYSize
    geotransform = source_dataset.GetGeoTransform()
    projection = source_dataset.GetProjectionRef()
    in_band = source_dataset.GetRasterBand(1)

    out_file = os.path.splitext(in_file)[0] + '_sieve.tif'
    if os.path.exists(out_file):
        os.remove(out_file)

    out_driver = gdal.GetDriverByName('GTiff')
    out_dataset = out_driver.Create(out_file, xsize, ysize, 1, gdal.GDT_Byte)
    out_band = out_dataset.GetRasterBand(1)

    result_sieve = gdal.SieveFilter(in_band, None, out_band, 2**10, 4, callback = None)

    data = out_band.ReadAsArray(0, 0, xsize, ysize)
    if len(data[np.where(data == 1)]) <= 2 ** 10:
        sys.exit('the number of water point too few, can not do Raster To Polygon')

    out_band.SetNoDataValue(0)

    out_dataset.SetGeoTransform(geotransform)
    out_dataset.SetProjection(projection)
    source_dataset = None
    out_dataset = None

    return out_file

def clourd_img(in_file, out_file):
    source_dataset = gdal.Open(in_file)
    if source_dataset is None:
        sys.exit('Problem opening file %s !' % in_file)

    # 获取数据基本信息
    xsize = source_dataset.RasterXSize
    ysize = source_dataset.RasterYSize
    num_band = source_dataset.RasterCount
    geotransform = source_dataset.GetGeoTransform()
    projection = source_dataset.GetProjectionRef()
    data_type = source_dataset.GetRasterBand(1).DataType

    if num_band < 4:
        sys.exit('number of band is %d ! ' % num_band)

    if os.path.exists(out_file):
        os.remove(out_file)

    out_data = np.zeros((ysize, xsize), dtype=np.uint8)

    blue_data = source_dataset.GetRasterBand(1).ReadAsArray(0, 0, xsize, ysize).astype(np.float32) / 10000
    red_data = source_dataset.GetRasterBand(3).ReadAsArray(0, 0, xsize, ysize).astype(np.float32) / 10000

    cloud_ind = np.where((blue_data > 0.15) | (red_data > 0.18))

    if len(out_data[cloud_ind]) > 255:
        out_data[cloud_ind] = 1
    else:
        sys.exit('no cloud')

    driver = gdal.GetDriverByName('GTiff')
    out_dataset = driver.Create(out_file, xsize, ysize, 1, gdal.GDT_Byte)
    out_band = out_dataset.GetRasterBand(1)

    out_band.WriteArray(out_data, 0, 0)

    out_band.SetNoDataValue(0)
    blue_data = None
    red_data = None
    out_data = None

    out_dataset.SetGeoTransform(geotransform)
    out_dataset.SetProjection(projection)
    out_dataset = None
    out_band = None

def main(in_file, shapefile):

    temp_dir = os.path.join(tempfile.gettempdir(), 'temp_gdal_tian')
    if not os.path.isdir(temp_dir):
        os.mkdir(temp_dir)

    cloud_raster_file = os.path.join(temp_dir, '%s_cloud.tif' % (os.path.splitext(os.path.basename(in_file))[0]))
    clourd_img(in_file, cloud_raster_file)

    shp_file = raster2shp(temp_dir, sieve_filter(cloud_raster_file))
    reproject_shape(shp_file, shapefile)

    shutil.rmtree(temp_dir)


if __name__ == '__main__':
    start_time = time.time()

    if len(sys.argv[1:]) < 2:
        sys.exit('Problem reading input')

    main(sys.argv[1], sys.argv[2])
    # in_file = r"D:\Data\Test_data\Input\GF2_PMS1_E113.6_N33.9_20180515_L1A0003188077\GF2_PMS1_E113.6_N33.9_20180515_L1A0003188077-MSS1_ort_app.tif"
    # out_file = r"D:\Data\Test_data\Input\GF2_PMS1_E113.6_N33.9_20180515_L1A0003188077\GF2_PMS1_E113.6_N33.9_20180515_L1A0003188077-MSS1_ort_app_cloud_shp2.shp"
    # main(in_file, out_file)

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))