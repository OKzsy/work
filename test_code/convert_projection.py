#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Describe: convert map projection and resample of modis
# Author: tianjg
# Create date: 2017.4.20 13:45
__author__ = 'tianjg'
import os

try:
    from osgeo import gdal, gdalconst, osr
except ImportError:
    import gdal, gdalconst, osr


# 文件直角坐标转成文件地理坐标
def to_geo(fileX, fileY, file_geo):
    geoX = file_geo[0] + fileX * file_geo[1]
    geoY = file_geo[3] + fileY * file_geo[5]
    return geoX, geoY

# 设置MODIS输出文件的像元大小
def set_pixel_size(file_geo):
    if file_geo[1] > 0 and file_geo[1] <= 250:
        pixel_size = 250.0
    elif file_geo[1] > 250 and file_geo[1] <= 500:
        pixel_size = 500.0
    elif file_geo[1] > 500 and file_geo[1] <= 1000:
        pixel_size = 1000.0
    else:
        print("can't set pixel size")
    return pixel_size


# filename = 'D:/Download/MOD13A2.A2000049.h25v03.006.2015136104647_2.tif'
# in_file = r'D:\实施项目\农科院草地室测试数据\内蒙古16天NDVI\内蒙古16天NDVI\2000_h26v04_SIN\MOD13A2.A2000049.h26v04.006_sin.tif'
# in_file = r'D:\实施项目\灾害要素日常遥感监测工具集成\newTestData\MOD13A2.A2001305_sin_mosaic_IDL.tif'
# in_file = r'D:\实施项目\农科院草地室测试数据\测试输出\MOD13A3.A2000.h26v04_mul_sin.dat'
# in_file = r'D:\实施项目\灾害要素日常遥感监测工具集成\newTestData\2001305_NDVI_mosaic_py.tif'
in_file = r'D:\实施项目\农科院草地室测试数据\内蒙古16天NDVI\内蒙古16天NDVI\MOD13A2.A2000209_mosaic_gdal.tif'
# out_file = 'D:/Download/MOD13A3.A2000.h26v04_mul_cp.tif'
# out_file = r'D:\实施项目\灾害要素日常遥感监测工具集成\newTestData\MOD13A2.A2001305_sin_mosaic_cp_gdal.tif'
out_file = r'D:\实施项目\农科院草地室测试数据\内蒙古16天NDVI\内蒙古16天NDVI\MOD13A2.A2000209_mosaic_proj_resam_gdal.tif'
# filename = r'D:\实施项目\农科院草地室测试数据\内蒙古16天NDVI\内蒙古16天NDVI\2000_h26v04_mosaic\MOD13A2.A2000049.h26v04.006_sin_mosaic.tif'
dataset = gdal.Open(in_file)
if dataset is None:
    print('Problem opening file %s !' % in_file)
else:
    print('File %s is fine.' % in_file)

# 获取数据基本信息
xsize = dataset.RasterXSize
ysize = dataset.RasterYSize
band_count = dataset.RasterCount
band1 = dataset.GetRasterBand(1)

in_geo = dataset.GetGeoTransform()
in_proj = dataset.GetProjectionRef()
in_proj_wkt = osr.SpatialReference()
in_proj_wkt.ImportFromWkt(in_proj)

# set out file projection
out_proj = osr.SpatialReference()
# out_proj.ImportFromEPSG(4326)
out_proj.SetProjCS('ACEA/WGS84')
out_proj.SetWellKnownGeogCS("WGS84")
out_proj.SetACEA(25.0, 47.0, 0.0, 105.0, 0.0, 0.0)
out_proj.SetLinearUnits('metre', 1)

# proj="""PROJCS["unnamed",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433],AUTHORITY["EPSG","4326"]],PROJECTION["Albers_Conic_Equal_Area"],PARAMETER["standard_parallel_1",25],PARAMETER["standard_parallel_2",47],PARAMETER["latitude_of_center",0],PARAMETER["longitude_of_center",105],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]]]"""
# proj="""PROJCS["unnamed",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Albers_Conic_Equal_Area"],PARAMETER["standard_parallel_1",25],PARAMETER["standard_parallel_2",47],PARAMETER["latitude_of_center",0],PARAMETER["longitude_of_center",105],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1]]"""

# out_proj.ImportFromWkt(proj)
# print(out_proj.ExportToWkt())
# 原左上角坐标
top_left_geoX, top_Left_geoY = to_geo(0, 0, in_geo)
# 原右上角坐标
top_right_geoX, top_right_geoY = to_geo(xsize, 0, in_geo)
# 原左下角坐标
bottom_left_geoX, bottom_left_geoY = to_geo(0, ysize, in_geo)
# 原右下角坐标
bottom_right_geoX, bottom_right_geoY = to_geo(xsize, ysize, in_geo)

# 四角坐标转换
ct = osr.CoordinateTransformation(in_proj_wkt, out_proj)
out_tl_geoX, out_tl_geoY, temp = ct.TransformPoint(top_left_geoX, top_Left_geoY, 0)
out_tr_geoX, out_tr_geoY, temp = ct.TransformPoint(top_right_geoX, top_right_geoY, 0)
out_bl_geoX, out_bl_geoY, temp = ct.TransformPoint(bottom_left_geoX, bottom_left_geoY, 0)
out_br_geoX, out_br_geoY, temp = ct.TransformPoint(bottom_right_geoX, bottom_right_geoY, 0)

out_min_geoX = min(out_tl_geoX, out_tr_geoX, out_bl_geoX, out_br_geoX)
out_max_geoX = max(out_tl_geoX, out_tr_geoX, out_bl_geoX, out_br_geoX)

out_min_geoY = min(out_tl_geoY, out_tr_geoY, out_bl_geoY, out_br_geoY)
out_max_geoY = max(out_tl_geoY, out_tr_geoY, out_bl_geoY, out_br_geoY)

# 设置输出文件的地理坐标
out_ps = set_pixel_size(in_geo)
out_ps1 = in_geo[1]
out_ps2 = in_geo[5]
out_geo = (out_min_geoX, out_ps, 0, out_max_geoY, 0, -out_ps)
# 设置输出文件行列号
out_xsize = int((out_max_geoX - out_min_geoX) / out_geo[1] + 0.5)
out_ysize = int((out_min_geoY - out_max_geoY) / out_geo[5] + 0.5)

# output TIFF file
if os.path.exists(out_file):
    os.remove(out_file)
out_driver = gdal.GetDriverByName('GTiff')
out_dataset = out_driver.Create(out_file, out_xsize, out_ysize, band_count, band1.DataType)

# set NoData to -3000
for i in range(band_count):
    out_band = out_dataset.GetRasterBand(i + 1)
    out_band.Fill(-3000)

# set -3000 to NoData
# outBand.SetNoDataValue(-3000)

# set coordinate and projection of outData
out_dataset.SetGeoTransform(out_geo)
out_dataset.SetProjection(out_proj.ExportToWkt())
# 重新投影和重采样
res = gdal.ReprojectImage(dataset, out_dataset, in_proj, out_proj.ExportToWkt(), gdal.GRA_NearestNeighbour)
print('-------------->>>>>>>>>>>>>>>>>end')