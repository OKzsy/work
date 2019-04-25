#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/10/9 17:53

Description:
    根据导出的光谱文本文件，生成csv光谱文件

Parameters
    参数1：光谱仪导出文本的文件夹路径
    参数2：输出csv文件路径
    参数3：光谱仪一个点需要测量的次数,默认为5

"""

import os
import sys
import time
import csv
import random
import string
import tempfile
import shutil
import operator
import numpy as np


try:
    from osgeo import gdal, ogr
except ImportError:
    import gdal, ogr

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def search_file(folder_path, file_extension):
    search_files = {}
    for dirpath, dirnames, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(file_extension):
                file_name = os.path.splitext(file)[0]
                if file_name[:8] == 'spectrum':
                    file_id = np.int(os.path.splitext(file)[0][8:13])
                else:
                    file_id = os.path.splitext(file)[0][5:10]
                search_files[file_id] = (os.path.normpath(os.path.join(dirpath, file)))
    return search_files

def get_mean_data(txt_files):
    txt_dict = {}
    for itxt in range(len(txt_files)):
        itxt_data = []
        with open(list(txt_files[itxt])[1], 'rb') as in_txt:
            for line in in_txt.readlines():
                line_data = line.decode('utf-8').replace('\r', '').replace('\n', '').split('\t')
                itxt_data.append(line_data[-1])
        txt_dict[itxt] = itxt_data
    # txt data to array
    xsize = len(txt_dict)
    ysize = len(txt_dict[0])

    txt_data = []

    for itxt_dict in txt_dict:
        txt_data = txt_data + txt_dict[itxt_dict]
    txt_array = np.array(txt_data).reshape(xsize, ysize).astype(np.float)

    mean_array = np.mean(txt_array, 0)

    return mean_array, len(mean_array)


def get_band(txt_file):
    band_name = []
    with open(txt_file, 'rb') as in_txt:
        for line in in_txt.readlines():
            line_data = line.decode('utf-8').replace('\r', '').replace('\n', '').split('\t')
            band_name.append(float(line_data[-2]))
    return band_name

def main(in_dir, out_file):

    # out_file = os.path.join(out_dir, '%s.csv' % os.path.basename(in_dir))

    txt_dict = search_file(in_dir, '.txt')

    # 按照序号排序
    txt_list = sorted(txt_dict.items(), key=operator.itemgetter(0), reverse=False)

    # 获取波段名
    band_name = get_band(list(txt_list[0])[1])

    mean_data = np.array([])
    mean_data_xsize = int(len(txt_list) / num_asd) + 1
    mean_data = np.concatenate((mean_data, band_name))

    # 每5个文件分割
    for itxt in range(0, len(txt_list), num_asd):
        itxt_list = txt_list[itxt: itxt+num_asd]
        imean_data, isize = get_mean_data(itxt_list)
        mean_data = np.concatenate((mean_data, imean_data))

    mean_array = mean_data.reshape(mean_data_xsize, len(band_name))

    # 灰白黑各45个点
    out_csv_head = [r'band\id' , 0] + \
                   ['g%d' % (i+1) for i in range(45)] + ['b%d' % (i+1) for i in range(45)] + ['w%d' % (i+1) for i in range(45)]
    with open(out_file, 'w', newline='') as out_csv:
        out_csv_writer = csv.writer(out_csv, dialect=("excel"))
        out_csv_writer.writerow(out_csv_head)

        for iband in range(len(band_name)):
            band_data = mean_array[:, iband]
            out_csv_writer.writerow(band_data.tolist())

if __name__ == '__main__':

    start_time = time.time()

    if len(sys.argv[1:]) < 3:
        sys.exit('Problem reading input')

    in_dir = sys.argv[1]
    out_file = sys.argv[2]

    # in_dir = r'D:\Data\Test_data\radiation_calobration\planet_2018080711\20180807嵩山\20180807手持导出'
    # out_file = r"D:\Data\Test_data\radiation_calobration\planet_2018080711\2018080711_HH2.csv"
    num_asd = int(sys.argv[3])

    main(in_dir, out_file)

    end_time = time.time()
    print('time: %.2f min.' % ((end_time - start_time) / 60))

