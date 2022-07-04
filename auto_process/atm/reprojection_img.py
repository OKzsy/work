#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/3/29 9:30

Description:
    convert raster projection

Parameters
    in_file: input file path
    out_pixel: size of pixel(meter)
    out_file: output file path
    out_proj: out projection(options)

"""



import os, sys, time

from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress



# 文件直角坐标转成文件地理坐标
def to_geo(fileX, fileY, file_geo):
    geoX = file_geo[0] + fileX * file_geo[1]
    geoY = file_geo[3] + fileY * file_geo[5]
    return geoX, geoY


def main(in_file, out_pixel, out_file):

    source_dataset = gdal.Open(in_file)
    if source_dataset is None:
        sys.exit('Problem opening file %s !' % in_file)

    # 获取数据基本信息
    xsize = source_dataset.RasterXSize
    ysize = source_dataset.RasterYSize
    num_band = source_dataset.RasterCount
    data_type = source_dataset.GetRasterBand(1).DataType

    in_geo = source_dataset.GetGeoTransform()
    in_proj = source_dataset.GetProjectionRef()

    in_proj_wkt = osr.SpatialReference()
    in_proj_wkt.ImportFromWkt(in_proj)

    # set out file projection
    out_proj_wkt = osr.SpatialReference()
    out_proj_wkt.ImportFromEPSG(4326)

    # 原左上角坐标
    top_left_geoX, top_Left_geoY = to_geo(0, 0, in_geo)
    # 原右上角坐标
    top_right_geoX, top_right_geoY = to_geo(xsize, 0, in_geo)
    # 原左下角坐标
    bottom_left_geoX, bottom_left_geoY = to_geo(0, ysize, in_geo)
    # 原右下角坐标
    bottom_right_geoX, bottom_right_geoY = to_geo(xsize, ysize, in_geo)

    # 四角坐标转换
    ct = osr.CoordinateTransformation(in_proj_wkt, out_proj_wkt)
    out_tl_geoX, out_tl_geoY, temp = ct.TransformPoint(top_left_geoX, top_Left_geoY, 0)
    out_tr_geoX, out_tr_geoY, temp = ct.TransformPoint(top_right_geoX, top_right_geoY, 0)
    out_bl_geoX, out_bl_geoY, temp = ct.TransformPoint(bottom_left_geoX, bottom_left_geoY, 0)
    out_br_geoX, out_br_geoY, temp = ct.TransformPoint(bottom_right_geoX, bottom_right_geoY, 0)

    out_min_geoX = min(out_tl_geoX, out_tr_geoX, out_bl_geoX, out_br_geoX)
    out_max_geoX = max(out_tl_geoX, out_tr_geoX, out_bl_geoX, out_br_geoX)

    out_min_geoY = min(out_tl_geoY, out_tr_geoY, out_bl_geoY, out_br_geoY)
    out_max_geoY = max(out_tl_geoY, out_tr_geoY, out_bl_geoY, out_br_geoY)

    # 设置输出文件的地理坐标
    out_ps = out_pixel
    # out_ps = set_pixel_size(in_geo)
    out_geo = (out_min_geoX, out_ps, 0, out_max_geoY, 0, -out_ps)
    # 设置输出文件行列号
    out_xsize = int((out_max_geoX - out_min_geoX) / out_geo[1] + 0.5)
    out_ysize = int((out_min_geoY - out_max_geoY) / out_geo[5] + 0.5)

    # output TIFF file
    out_driver = gdal.GetDriverByName('GTiff')
    if os.path.exists(out_file):
        out_driver.Delete(out_file)
    out_dataset = out_driver.Create(out_file, out_xsize, out_ysize, num_band, data_type)

    # set coordinate and projection of outfile
    out_dataset.SetGeoTransform(out_geo)
    out_dataset.SetProjection(out_proj_wkt.ExportToWkt())

    # set NoData to 0 and fille vaule is 0
    for i in range(num_band):

        band = source_dataset.GetRasterBand(i + 1)

        if band.GetNoDataValue() is None:
            no_data = 0
        else:
            no_data = band.GetNoDataValue()
        out_band = out_dataset.GetRasterBand(i + 1)
        out_band.SetNoDataValue(no_data)
        # out_band.Fill(no_data)
        # out_band.Fill(-3000)
        # out_band.SetNoDataValue(-3000)

    # 重新投影和重采样
    res = gdal.ReprojectImage(source_dataset, out_dataset, in_proj, out_proj_wkt.ExportToWkt(),
                              gdal.GRA_NearestNeighbour, callback=progress, WarpMemoryLimit=2048)

    source_dataset = None
    out_dataset = None



if __name__ == '__main__':

    print('program running')

    start_time = time.time()

    # if len(sys.argv[1:]) < 3:
    #     sys.exit('Problem reading input')
    # if len(sys.argv[1:]) == 4:
    #     input_proj = sys.argv[4]
    # if len(sys.argv[1:]) == 3:
    #     input_proj = None

    # main(sys.argv[1], sys.argv[2], sys.argv[3])

    in_file = r"D:\Download\20181119_023935_103c_3B_AnalyticMS-atm.tif_test.tif"
    out_pixel = 0.00004
    out_file = r"D:\Download\20181119_023935_103c_3B_AnalyticMS-atm.tif_test_re.tif"
    main(in_file, out_pixel, out_file)



    end_time = time.time()
    print('\n' + "time: %.2f min." % ((end_time - start_time) / 60))