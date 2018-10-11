#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = 'tianjg'

import os
import shutil
import numpy as np

try:
    from osgeo import gdal, gdalconst, osr
except ImportError:
    import gdal, gdalconst, osr
# make temp dir
temp_dir = 'C:\\read_hdf\\'
if not os.path.isdir(temp_dir):
    os.mkdir("C:\\read_hdf\\")
dict_ext = ".hdf.HDF"
# in_file = "D:\\实施项目\\农科院草地室测试数据\\MOD09A1.A2000209.h25v03.005.2006305124212.hdf"
# out_flle = "D:\\实施项目\\农科院草地室测试数据\\MOD09A1_py_gdal.tif"
in_file = r"D:\实施项目\广西灾害遥感应用\测试数据\OMI-Aura_L3-OMTO3e_2017m0705_v003-2017m0707t021221.he5"
out_flle = r"D:\实施项目\广西灾害遥感应用\测试数据\OMI-Aura_L3-OMTO3e_2017m0705_v003-2017m0707t021221_sds0.tif"



new_file = temp_dir + os.path.basename(in_file)

if os.path.exists(new_file):
    os.remove(new_file)

shutil.copy(in_file, temp_dir)

#open file
sds = gdal.Open(new_file)
# 判断HDF文件是否符合要求
if sds is None:
    print('Problem opening file %s !' % new_file)
else:
    print('File %s is fine.' % new_file)
sub_sds = sds.GetSubDatasets()
source_dataset = gdal.Open(sub_sds[0][0])
print(sub_sds[0][0])

meta_data = source_dataset.GetMetadata()


cols = source_dataset.RasterXSize
rows = source_dataset.RasterYSize
bands = source_dataset.RasterCount
geotransform = source_dataset.GetGeoTransform()
projection = source_dataset.GetProjectionRef()
# proj_wkt = osr.SpatialReference()
# proj_wkt.ImportFromWkt(proj)
# print(proj_wkt)

driver = gdal.GetDriverByName('GTiff')
outData = driver.Create(out_flle, cols, rows, bands, gdal.GDT_Int16)
outBand = outData.GetRasterBand(1)
#read data
b1_data = source_dataset.GetRasterBand(1).ReadAsArray(0,0,cols,rows).astype(np.int16)
#
print(np.min(b1_data), np.max(b1_data))

outBand.WriteArray(b1_data)

# set coordinate and projection of outData
outData.SetGeoTransform(geotransform)
outData.SetProjection(projection)
#
# #
b1 = None; sub_sds =None
outData = None; sds = None; b1_data = None
#
shutil.rmtree(temp_dir)
print ('End')