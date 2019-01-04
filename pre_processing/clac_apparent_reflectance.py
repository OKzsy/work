#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/6/25 14:05

Description:
    根据定标系数(增益和偏移)计算辐亮度，再利用辐亮度数据和日地距离、ESUN、太阳天顶角等参数输出表观反射率(*10000)


Parameters
    in_file: DN影像路径
    out_file: 输出表观反射率数据路径

"""

import os
import sys
import time
import json
import math
import shutil
import xml.etree.ElementTree as ET
import datetime
import numpy as np
import numexpr as ne

try:
    from osgeo import gdal, osr
except ImportError:
    import gdal, osr

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress

# def calc_solar_zenith():



def reprojection(in_proj, mapx, mapy):
    in_proj_wkt = osr.SpatialReference()
    in_proj_wkt.ImportFromWkt(in_proj)

    # set wgs84 projection
    out_proj = osr.SpatialReference()
    out_proj.ImportFromEPSG(4326)

    ct = osr.CoordinateTransformation(in_proj_wkt, out_proj)
    out_mapx, out_mapy, temp = ct.TransformPoint(mapx, mapy, 0)

    return out_mapx, out_mapy
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

def file_info(in_file, out_file):
    in_xml_file = os.path.splitext(in_file)[0] + '.xml'

    in_json_file = os.path.splitext(in_file)[0] + '.json'


    info_list = []
    if os.path.exists(in_xml_file):

        out_xml_file = os.path.join(os.path.dirname(out_file),
                                    '%s.xml' % os.path.splitext(os.path.basename(out_file))[0])
        shutil.copy(in_xml_file, out_xml_file)

        tree = ET.parse(in_xml_file)
        root = tree.getroot()

        tag_list = ['ReceiveTime', 'SatelliteID', 'SensorID', 'Bands', 'SolarZenith']

        for itag in tag_list:
            for child_root in root:
                if child_root.tag == itag:
                    info_list.append(child_root.text)
        # 重新定义参量
        info_list[0] = info_list[0].replace(' ', '-').replace(':', '-')
        info_list[3] = len(info_list[3].split(','))
        info_list[4] = float(info_list[4])

    if os.path.exists(in_json_file):
        out_json_file = os.path.join(os.path.dirname(out_file),
                                    '%s.json' % os.path.splitext(os.path.basename(out_file))[0])
        shutil.copy(in_json_file, out_json_file)

        source_dataset = gdal.Open(in_file)
        num_band = source_dataset.RasterCount
        source_dataset = None
        with open(in_json_file, 'r') as in_json:
            json_data = json.load(in_json)['properties']

            info_list.append(json_data['acquired'].replace('T', '-').replace(':', '-'))
            info_list.append(json_data['satellite_id'])
            info_list.append(json_data['camera_id'])
            info_list.append(num_band)
            info_list.append(90 - float(json_data['sun_elevation']))

    return info_list


def main(in_file, out_file):

    # 影像采集时间,卫星ID,传感器ID,波段数,太阳天顶角(度)
    info_list = file_info(in_file, out_file)

    if info_list == []:
        sys.exit('no metadata')


    """
    字典须根据实际情况进行扩展
    """

    dict_gain = {'GF2':{'PMS1':[0.1193, 0.1530, 0.1530, 0.1569, 0.1503], 'PMS2':[0.1434, 0.1595, 0.1511, 0.1685, 0.1679]},
                 'GF1':{'PMS1':[0.1424, 0.1177, 0.1194, 0.1135, 0.1228], 'PMS2':[0.1460, 0.1248, 0.1274, 0.1255, 0.1365]},
                 'SSC6':[0.2474, 0.1332, 0.1110, 0.1255, 0.0715]}
    dict_bias = {'GF2':{'PMS1':[0.0, 0.0, 0.0, 0.0, 0.0], 'PMS2':[0.0, 0.0, 0.0, 0.0, 0.0]},
                 'GF1':{'PMS1':[0.0, 0.0, 0.0, 0.0, 0.0], 'PMS2':[0.0, 0.0, 0.0, 0.0, 0.0]},
                 'SSC6':[-59.940, -27.919, -24.487, -44.010, -49.873]}

    dict_ESUN = {'GF2':{'PMS1':[1941.53, 1854.15, 1541.48, 1086.43, 1364.03], 'PMS2':[1940.93, 1853.99, 1541.39, 1086.51, 1361.93]},
                 'GF1':{'PMS1':[1944.98, 1854.42, 1542.63, 1080.81, 1371.53], 'PMS2':[1945.34, 1854.15, 1543.62, 1081.93, 1376.10]},
                 'SSC6':[2009.28, 1820.25, 1583.3, 1114.22, 1582.79]}


    if isinstance(dict_gain[info_list[1]], dict):

        if info_list[3] > 1:
            in_gain = dict_gain[info_list[1]][info_list[2]][0:-1]
            in_bias = dict_bias[info_list[1]][info_list[2]][0:-1]
            in_ESUN = dict_ESUN[info_list[1]][info_list[2]][0:-1]
        else:
            in_gain = dict_gain[info_list[1]][info_list[2]][-1]
            in_bias = dict_bias[info_list[1]][info_list[2]][-1]
            in_ESUN = dict_ESUN[info_list[1]][info_list[2]][-1]

    else:
        if info_list[3] > 1:
            in_gain = dict_gain[info_list[1]][0:-1]
            in_bias = dict_bias[info_list[1]][0:-1]
            in_ESUN = dict_ESUN[info_list[1]][0:-1]
        else:
            in_gain = dict_gain[info_list[1]][-1]
            in_bias = dict_bias[info_list[1]][-1]
            in_ESUN = dict_ESUN[info_list[1]][-1]
    in_pi = math.pi
    acquired_time = info_list[0].split('-')

    format_time = datetime.datetime(int(acquired_time[0]), int(acquired_time[1]), int(acquired_time[2]))
    day_of_year = (format_time - datetime.datetime(int(acquired_time[0]), 1, 1)).days + 1
    # 日角
    day_angle = 2 * math.pi * day_of_year / 365
    # 计算日地距离
    earth_sun_distance = 1.000110 + 0.034221 * math.cos(day_angle) + 0.00128 * math.sin(day_angle) + \
                         0.000719 * math.cos(2 * day_angle) + 0.000077 * math.sin(2 * day_angle)


    cos_theta = math.cos(math.radians(info_list[4]))

    source_dataset = gdal.Open(in_file)
    if source_dataset is None:
        sys.exit('Problem opening file %s!' % in_file)

    xsize = source_dataset.RasterXSize
    ysize = source_dataset.RasterYSize
    num_band = source_dataset.RasterCount
    geotransform = source_dataset.GetGeoTransform()
    projection = source_dataset.GetProjectionRef()

    out_driver = gdal.GetDriverByName('GTiff')

    if os.path.exists(out_file):
        out_driver.Delete(out_file)

    out_dataset = out_driver.Create(out_file, xsize, ysize, num_band, gdal.GDT_Int16)


    for iband in range(info_list[3]):

        in_band = source_dataset.GetRasterBand(1 + iband)

        if in_band.GetNoDataValue() is None:
            no_data = 0
        else:
            no_data = in_band.GetNoDataValue()

        in_data = in_band.ReadAsArray(0, 0, xsize, ysize).astype(np.float32)
        in_data[np.where(in_data == no_data)] = np.nan


        in_gain_band = in_gain[iband]
        in_bias_band = in_bias[iband]
        in_ESUN_band = in_ESUN[iband]

        # for yoffset in range(0, ysize, num_block):
        #     if yoffset + num_block < ysize:
        #         num_ysize = num_block
        #     else:
        #         num_ysize = ysize - yoffset
        #
        #     for xoffset in range(0, xsize, num_block):
        #         if xoffset + num_block < xsize:
        #             num_xsize = num_block
        #         else:
        #             num_xsize = xsize - xoffset
        #
        #         in_block_data = in_data[yoffset:yoffset+num_ysize, xoffset:xoffset+num_xsize]
        #         center_xind = int(xoffset + num_xsize / 2)
        #         center_yind = int(yoffset + num_xsize / 2)
        #
        #         center_mapx, center_mapy = pixel2map(center_xind, center_yind, geotransform)
        #
        #         re_center_mapx, re_center_mapy = reprojection(projection, center_mapx, center_mapy)
        # 计算TOA
        out_data = ne.evaluate(
            '10000.0 * (in_gain_band * in_data + in_bias_band) * in_pi * (earth_sun_distance * earth_sun_distance) / (in_ESUN_band * cos_theta)')


        out_data[np.isnan(out_data)] = 0

        out_band = out_dataset.GetRasterBand(1 + iband)
        out_band.WriteArray(out_data, 0, 0)
        out_band.SetNoDataValue(0)

        progress((1 + iband) / num_band)

        in_data = None
        out_data = None
        in_band = None
        out_band = None

    out_dataset.SetGeoTransform(geotransform)
    out_dataset.SetProjection(projection)

    source_dataset = None
    out_dataset = None



if __name__ == '__main__':

    start_time = time.time()

    if len(sys.argv[1:]) < 2:
        sys.exit('Problem reading input')
    main(sys.argv[1], sys.argv[2])

    # in_file = r"D:\Data\Test_data\un_zip\out_dir\GF2_PMS2_E114.0_N34.7_20180327_L1A0003087399_mss2_ort.tif"
    # out_file = r"D:\Data\Test_data\un_zip\out_dir\GF2_PMS2_E114.0_N34.7_20180327_L1A0003087399_mss2_ort_app.tif"
    #
    # in_file = r"D:\Data\Test_data\un_zip\out_dir\planet_order_173849\20180325_033627_ss01d1_0024_analytic_dn_ort.tif"
    # out_file = r"D:\Data\Test_data\un_zip\out_dir\planet_order_173849\20180325_033627_ss01d1_0024_analytic_dn_ort_app.tif"

    # main(in_file, out_file)

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))