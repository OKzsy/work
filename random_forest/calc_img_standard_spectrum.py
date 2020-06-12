#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/12/20 11:20

Description:
    计算影像标准光谱

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


def get_flag_dict(folder_path, file_extension):
    # 获取flag标签和样本所在位置
    flag = []
    search_files = []
    for dir_path, dir_names, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(file_extension):
                flag.append(str(os.path.splitext(file)[0].split('-')[-1]))
                search_files.append(os.path.normpath(os.path.join(dir_path, file)))
    flag_set = list(set(flag))  # 去掉重复flag
    flag_set.sort()  # 排序
    out_dict = {}
    for iflag in flag_set:
        iflag_list = []
        for ifile in search_files:
            file_flag = str(os.path.splitext(os.path.basename(ifile))[0].split('-')[-1])
            if file_flag == iflag:
                iflag_list.append(ifile)
        out_dict[iflag] = iflag_list
    return out_dict


def get_standard_spectrum(in_files):
    box_scale = 1.5
    num_band = gdal.Open(in_files[0]).RasterCount

    spec_array = np.zeros((num_band, 1), dtype=np.int16)
    for ifile in range(len(in_files)):
        isds = gdal.Open(in_files[ifile])
        ixsize = isds.RasterXSize
        iysize = isds.RasterYSize
        idata = isds.ReadAsArray().reshape(num_band, ixsize * iysize)
        ind_nodata = np.where(idata[0, :] != 0)

        isub_data = []
        for iband in range(num_band):
            isub_data.append(idata[iband, :][ind_nodata])
        spec_array = np.column_stack((spec_array, np.array(isub_data)))

        idata = None
        isub_data = None

    spec_array = spec_array[:, 1:]

    ind_data = np.zeros((1, spec_array.shape[1]), dtype=np.byte)

    for iband in range(num_band):
        iband_data = spec_array[iband, :].reshape(1, spec_array.shape[1])
        # 四分位筛选
        band_low = np.percentile(iband_data, 25)
        band_upper = np.percentile(iband_data, 75)
        band_inter = (band_low - box_scale * (band_upper - band_low),
                      box_scale * (band_upper - band_low) + band_upper)

        ind_useful = np.where((iband_data >= band_inter[0]) & (iband_data <= band_inter[1]))
        ind_data[ind_useful] = 1
        iband_data = None
        ind_useful = None

    # 标准光谱数据集
    ind = np.where(ind_data == 1)

    stand_spec = []
    for iband in range(num_band):
        iband_data = spec_array[iband, :].reshape(1, spec_array.shape[1])
        stand_spec.append(iband_data[ind])
    stand_spec = np.array(stand_spec)
    stand_spec_mean = np.mean(stand_spec, axis=1).tolist()
    stand_spec = None
    spec_array = None

    return stand_spec_mean


def main(in_dir, out_csv_file):
    print('get img files start...')
    flag_dict = get_flag_dict(in_dir, '.tif')
    flag_list = list(flag_dict.keys())
    print('get img files done.')

    # 写入csv
    print('get falg standard spectrum start...')
    out_csv = open(out_csv_file, 'w', newline='')
    out_csv_writer = csv.writer(out_csv)

    for iflag in range(len(flag_list)):
        flag_files = flag_dict[flag_list[iflag]]
        flag_stand = get_standard_spectrum(flag_files)

        out_csv_writer.writerow([flag_list[iflag]] + flag_stand)
        progress((iflag + 1) / len(flag_list))

    out_csv.close()
    out_csv_writer = None
    print('get falg standard spectrum done.')


if __name__ == '__main__':
    start_time = time.time()

    # if len(sys.argv[1:]) < 2:
    #     sys.exit('Problem reading input')
    #
    # in_dir = sys.argv[1]
    # out_csv_file = sys.argv[2]

    in_dir = r'\\192.168.0.234\nydsj\user\ZSS\shanyao\sample'
    out_csv_file = r'\\192.168.0.234\nydsj\user\ZSS\shanyao\sample\sample2.csv'
    main(in_dir, out_csv_file)

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))
