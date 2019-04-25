#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/6/10 13:08

Description:
    利用经纬度坐标，提取影像的DN值

Parameters
    参数1：输入经过几何精校正影像的路径
    参数2：经纬度csv坐标文件路径
    参数3：输出提取的DN值文件路径

"""

import os
import sys
import time
import csv
import numpy as np

try:
    from osgeo import gdal, osr
except ImportError:
    import gdal, osr

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress

# 文件地理坐标转成文件直角坐标
def geo2point(geox, geoy, file_geo):
    filex = (geox - file_geo[0]) / file_geo[1]
    filey = (geoy - file_geo[3]) / file_geo[5]

    return int(filex+0.5), int(filey+0.5)


def main(img_file, point_map_file, out_file):


    latitude_list = []
    longitude_list = []
    point_name = []
    with open(point_map_file, 'r') as point_csv:

        csv_data = point_csv.readlines()

        for icsv_data in csv_data:
            latitude_list.append(np.float(icsv_data.split(',')[1]))
            longitude_list.append(np.float(icsv_data.split(',')[0]))
            point_name.append((icsv_data.replace('\n', '').split(',')[2]))

    # spectra_data = pd.read_excel(xls_file, sheet_name=3).get_values()

    latitude = np.array(latitude_list)
    longitude = np.array(longitude_list)
    point_name = np.array(point_name)

    source_dataset = gdal.Open(img_file)
    if source_dataset is None:
        sys.exit('Problem opening file %s !' % in_file)

    # 获取数据基本信息
    xsize = source_dataset.RasterXSize
    ysize = source_dataset.RasterYSize
    num_band = source_dataset.RasterCount
    data_type = source_dataset.GetRasterBand(1).DataType

    geotransform = source_dataset.GetGeoTransform()
    projection = source_dataset.GetProjectionRef()

    file_proj_wkt = osr.SpatialReference()
    file_proj_wkt.ImportFromWkt(projection)

    sample_proj_wkt = osr.SpatialReference()
    sample_proj_wkt.SetWellKnownGeogCS("WGS84")

    # 坐标转换 由sample_proj_wkt 转成 file_proj_wkt
    ct = osr.CoordinateTransformation(sample_proj_wkt, file_proj_wkt)

    sample2filex = np.asarray([], dtype=np.int64)
    sample2filey = np.asarray([], dtype=np.int64)

    for ipoint in range(len(latitude)):
        # longitude is x, latitude is y
        igeox, igeoy, temp = ct.TransformPoint(longitude[ipoint], latitude[ipoint], 0)
        sample2filex = np.append(sample2filex, np.int64(geo2point(igeox, igeoy, geotransform)[0]))
        sample2filey = np.append(sample2filey, np.int64(geo2point(igeox, igeoy, geotransform)[1]))

    ind = np.where(
        (sample2filex >= 0) & (sample2filex <= xsize - 1) & (sample2filey >= 0) & (sample2filey <= ysize - 1))

    if len(ind) < 1:
        sys.exit('No sample point in %s' % in_file)
    else:
        in_sample2filex = sample2filex[ind]
        in_sample2filey = sample2filey[ind]
        in_point_name = point_name[ind]


    # file_nd = np.asarray([], dtype=np.float32)
    print(len(in_sample2filey))

    out_csv = open(out_file, "w", newline='')

    csv_writer = csv.writer(out_csv)
    csv_writer.writerow(['point/band'] + ['band%d' %(i+1) for i in range(num_band)])

    for ifile_nd in range(len(in_sample2filex)):

        ifilex = np.int(in_sample2filex[ifile_nd])
        ifiley = np.int(in_sample2filey[ifile_nd])
        iout_data = [in_point_name[ifile_nd]]
        for iband in range(num_band):
            in_band = source_dataset.GetRasterBand(iband + 1)

            ifile_nd = in_band.ReadAsArray(ifilex, ifiley, 1, 1)
            ifile_nd = in_band.ReadAsArray()
            # print(ifile_nd[0][0])
            iout_data.append(np.float(ifile_nd[ifiley, ifilex]))
            in_data = None
            in_band = None
        csv_writer.writerow(iout_data)
    out_csv.close()
    csv_writer = None
    out_csv = None
    # file_nd = np.append(file_nd, ifile_nd)


if __name__ == '__main__':

    start_time = time.time()

    if len(sys.argv[1:]) < 3:
        sys.exit('Problem reading input')

    # in_file = r"D:\Data\Test_data\radiation_calobration\planet_2018080811\20180808_024005_1024_1B_AnalyticMS_DN_sub_sub_warp.dat"
    # csv_file = r"D:\Data\Test_data\radiation_calobration\planet_2018080811\point_lat_lon.csv"
    # out_csvfile  = r"D:\Data\Test_data\radiation_calobration\planet_2018080811\20180808_planet_dn_02.csv"
    #
    # in_file = r"D:\Data\Test_data\radiation_calobration\planet_2018080711\20180807_024047_1009_1B_AnalyticMS_DN_rpcortho_sub_warp2.tif"
    # csv_file = r"D:\Data\Test_data\radiation_calobration\planet_2018080711\sample_lon_lat_copy.csv"
    # out_csvfile = r"D:\Data\Test_data\radiation_calobration\planet_2018080711\planet_20180807_dn.csv"
    #
    # in_file = r"D:\Data\Test_data\radiation_calobration\planet_2018060513\Skysat8_20180605_M_rpcortho_clip_wrap_4.tif"
    # csv_file = r"D:\Data\Test_data\radiation_calobration\planet_2018060513\dian.csv"
    # out_csvfile = r"D:\Data\Test_data\radiation_calobration\planet_2018060513\Skysat8_20180605_M_dn.csv"

    in_file = sys.argv[1]
    csv_file = sys.argv[2]
    out_csvfile = sys.argv[3]


    main(in_file, csv_file, out_csvfile)

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))