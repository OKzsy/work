#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/7/12 19:43

Description:
    

Parameters
    

"""

import os
import sys
import csv
import time
import shutil
import numpy as np
try:
    from osgeo import gdal
except ImportError:
    import gdal

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def search_file(folder_path, file_extension):
    search_files = []
    for dir_path, dir_names, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(file_extension):
                search_files.append(os.path.normpath(os.path.join(dir_path, file)))
    return search_files


def main(in_file, in_dir, out_file):
    source_dataset = gdal.Open(in_file)

    if source_dataset is None:
        sys.exit('Problem opening file %s!' % in_file)

    xsize = source_dataset.RasterXSize
    ysize = source_dataset.RasterYSize
    num_band = source_dataset.RasterCount
    geotransform = source_dataset.GetGeoTransform()
    projection = source_dataset.GetProjectionRef()
    data_type = source_dataset.GetRasterBand(1).DataType

    out_driver = gdal.GetDriverByName('GTiff')
    # #
    if os.path.exists(out_file):
        out_driver.Delete(out_file)
    out_dataset = out_driver.Create(out_file, xsize, ysize, 1, gdal.GDT_Byte)
    out_band = out_dataset.GetRasterBand(1)

    out_data = np.empty((ysize, xsize), dtype=np.uint8)
    out_data[:, :] = 200

    csv_list = search_file(in_dir, '.csv')


    for icsv in range(len(csv_list)):
        # 读取csv
        with open(csv_list[icsv], 'r') as in_csv:
            csv_str = in_csv.readlines()

        for icsv_str in csv_str:
            icsv_data = icsv_str.replace('\n', '').split(',')

            # print(int(icsv_data[0]), int(icsv_data[1]), int(icsv_data[2]))
            out_data[int(icsv_data[0]), int(icsv_data[1])] = int(icsv_data[2])

        progress(icsv / len(csv_list))

    out_band.WriteArray(out_data, 0, 0)

    out_dataset.SetGeoTransform(geotransform)
    out_dataset.SetProjection(projection)

    source_dataset = None
    out_dataset = None
    out_band = None

    progress(1)



if __name__ == '__main__':
    start_time = time.time()

    if len(sys.argv[1:]) < 3:
        sys.exit('Problem reading input')
    main(sys.argv[1], sys.argv[2], sys.argv[3])
    # in_file = r"D:\Data\Test_data\un_zip\yingqiao_20180523+0607_reg_clip2.tif"
    # in_dir = r"D:\Data\Test_data\un_zip\out_dir\test5_class"
    # out_file = r"D:\Data\Test_data\un_zip\yingqiao_20180523+0607_reg_clip2_class5.tif"
    #
    # in_file = r"D:\Data\Test_data\classification\20180825\GF2_20180327_S20324_qingnianlu.tif"
    # in_dir = r"D:\Data\Test_data\classification\20180825\test_csv_class"
    # out_file = r"D:\Data\Test_data\classification\20180825\GF2_20180327_S20324_qingnianlu_class.tif"
    # main(in_file, in_dir, out_file)

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))

