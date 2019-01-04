#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/11/6 13:30

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

try:
    from osgeo import gdal, ogr
except ImportError:
    import gdal, ogr

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def clip(in_file, shapefile, out_file):
    # 单位为字节
    #
    sys_str = platform.system()
    if (sys_str == 'Windows'):
        warp_path = 'gdalwarp'
    else:
        warp_path = '/usr/local/bin/gdalwarp'
    #
    # clip_cmd_str = 'dumpbin /imports %s --config GDALWARP_IGNORE_BAD_CUTLINE YES -srcnodata %d -dstnodata %d -crop_to_cutline' \
    #                ' -cutline %s -of GTiff -r bilinear -overwrite -wm %d -wo NUM_THREADS=ALL_CPUS -co TILED=YES %s %s %s' \
    #                % (warp_path, 0, 0, shapefile, 4096, in_file, out_file, '> d:\log.txt')

    clip_cmd_str = '%s --config GDALWARP_IGNORE_BAD_CUTLINE YES -srcnodata %d -dstnodata %d -crop_to_cutline' \
                   ' -cutline %s -of GTiff -r bilinear -overwrite -wm %d -wo NUM_THREADS=ALL_CPUS -co TILED=YES %s %s' \
                   % (warp_path, 0, 0, shapefile, 4096, in_file, out_file)
    subprocess.call(clip_cmd_str, shell=True)

def main():

    temp_dir = os.path.join(tempfile.gettempdir(), 'gdal_interp')
    if not os.path.exists(temp_dir):
        os.mkdir(temp_dir)

    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    prov_dict = {'SX1': [109.89, 34.3065, 115.00, 40.912], 'SX2': [105.28, 31.59, 111.41, 39.71],
                 'HB': [112.0, 36.0, 120.01, 43.01], 'HN': [110.0, 31.0, 117.0, 36.0],
                 'NX': [104.0, 35.0, 107.7, 39.5], 'SC': [97.0, 26.0, 109.0, 34.5],
                 'SD': [114.5, 34.0, 123.0, 38.5]}
    #
    # prov = os.path.splitext(os.path.basename(out_pm25))[0].split('_')[-2]
    # city = os.path.splitext(os.path.basename(out_pm25))[0].split('_')[-1]


    with open(csv_file, 'r') as in_csv:
        csv_str = in_csv.readlines()

    head_line = csv_str[0].replace('\n', '').split(',')

    value_id = head_line[-3:]
    lon_ind = head_line.index('Lon')
    lat_ind = head_line.index('Lat')

    for ivalue in range(len(value_id)):
        ipm_csvfile = os.path.join(temp_dir, 'qixiang_interp_%s.csv'
                                   % (value_id[ivalue]))

        value_ind = head_line.index(value_id[ivalue])

        with open(ipm_csvfile, 'w', newline='') as ipm_csv:
            ipmcsv_writer = csv.writer(ipm_csv, dialect=("excel"))
            ipmcsv_writer.writerow(['Lon', 'Lat', 'Value'])
            for idata in csv_str[1:]:
                idata = idata.replace('\n', '').split(',')

                ipmcsv_writer.writerow([idata[lon_ind], idata[lat_ind], idata[value_ind]])

            # ipmcsv_writer = None
            # ipm_csv.close()

        ivrt_file = os.path.join(temp_dir,
                                 '%s_csv2vrt.vrt' % (os.path.splitext(os.path.basename(ipm_csvfile))[0]))

        ivrt_data = '<OGRVRTDataSource>\n' \
                    '  <OGRVRTLayer name="%s">\n' \
                    '    <SrcDataSource>%s</SrcDataSource>\n' \
                    '    <GeometryType>wkbPoint</GeometryType>\n' \
                    '    <LayerSRS>WGS84</LayerSRS>\n' \
                    '    <GeometryField encoding="PointFromColumns" x="Lon" y="Lat" z="%s"/>\n' \
                    '  </OGRVRTLayer>\n' \
                    '</OGRVRTDataSource>' % \
                    (os.path.splitext(os.path.basename(ipm_csvfile))[0], ipm_csvfile, 'Value')

        with open(ivrt_file, 'wb') as ivrt:
            ivrt.write(ivrt_data.encode("utf-8"))

        iout_file = os.path.join(out_dir, '%s.tif'
                                 % (os.path.splitext(os.path.basename(ipm_csvfile))[0]))

        tiff_driver = gdal.GetDriverByName("GTiff")
        if os.path.exists(iout_file):
            tiff_driver.Delete(iout_file)

        in_prov = 'HN'

        prov_extent = prov_dict[in_prov]
        prov_width = (prov_extent[2] - prov_extent[0]) / 0.005 + 1
        prov_height = (prov_extent[3] - prov_extent[1]) / 0.005 + 1

        gdal.Grid(iout_file, ivrt_file, format="GTiff", outputType=gdal.GDT_Float32,
                  algorithm='invdist:power=2.0:smoothing=0.0',
                  noData=0, width=prov_width, height=prov_height, outputBounds=prov_extent)

        clip_file = os.path.join(out_dir, '%s_sub.tif'
                                 % (os.path.splitext(os.path.basename(ipm_csvfile))[0]))

        clip(iout_file, shp_file, clip_file)
        os.remove(iout_file)

    shutil.rmtree(temp_dir)


if __name__ == '__main__':
    start_time = time.time()

    # if len(sys.argv[1:]) < 2:
    #     sys.exit('Problem reading input')
    csv_file = r"D:\Data\Test_data\visualization_20181106\qixiang\qixiang_site_value.csv"
    shp_file = r"D:\Data\Test_data\visualization_20181106\zhengzhou\zhengzhou\zhengzhou.shp"
    out_dir = r"D:\Data\Test_data\visualization_20181106\qixiang_interp"

    # ipm_csvfile = r"D:\Download\zhongmu_3_1_prec.csv"
    # iout_file = r"D:\Download\zhongmu_3_1_prec_csv2tif.tif"
    main()

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))