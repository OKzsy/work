#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/3/29 9:30

Description:
    利用四分位统计方法，筛选样本光谱

Parameters
    参数1：输入光谱文件
    参数2：输出筛选光谱文件

"""
import csv
import time
import sys
import pandas as pd
import numpy as np


def main(in_file, out_file):


    blue = 460
    green = 560
    red = 670
    red_edge = 700
    nir = 860

    # 读取实测光谱数据
    with open(in_file, 'r') as in_spec:
        spec_str = in_spec.readlines()

    point_names = spec_str[0].replace('\n', '').split(',')[1:]

    spec_data = []
    band_range = []

    for ispec_str in spec_str[1:]:
        ispec_data = ispec_str.replace('\n', '').split(',')
        spec_data.append([float(i) for i in ispec_data[1:]])
        band_range.append(int(ispec_data[0]))

    spec_array = np.array(spec_data)
    start_pos = band_range[0]

    num_point = int(spec_array.shape[1] / 3)
    # set output csv file
    out_csv = open(out_file, 'w', newline='')
    out_csv_writer = csv.writer(out_csv)

    for iblock in range(0, spec_array.shape[1], num_point):
        iblock_spec_array = spec_array[:, iblock: iblock + num_point]

        iblock_point_name = point_names[iblock: iblock + num_point]

        blue_data = iblock_spec_array[blue - start_pos][:]
        green_data = iblock_spec_array[green - start_pos][:]
        red_data = iblock_spec_array[red - start_pos][:]
        red_edge_data = iblock_spec_array[red_edge - start_pos][:]
        nir_data = iblock_spec_array[nir - start_pos][:]

        box_scale = 1.5
        blue_low = np.percentile(blue_data, 25)
        blue_upper = np.percentile(blue_data, 75)
        blue_inter = (blue_low - box_scale * (blue_upper - blue_low),
                      box_scale * (blue_upper - blue_low) + blue_upper)

        green_low = np.percentile(green_data, 25)
        green_upper = np.percentile(green_data, 75)
        green_inter = (green_low - box_scale * (green_upper - green_low),
                       box_scale * (green_upper - green_low) + green_upper)

        red_low = np.percentile(red_data, 25)
        red_upper = np.percentile(red_data, 75)
        red_inter = (red_low - box_scale * (red_upper - red_low),
                     box_scale * (red_upper - red_low) + red_upper)

        red_edge_low = np.percentile(red_edge_data, 25)
        red_edge_upper = np.percentile(red_edge_data, 75)
        red_edge_inter = (red_edge_low - box_scale * (red_edge_upper - red_edge_low),
                          box_scale * (red_edge_upper - red_edge_low) + red_edge_upper)

        nir_low = np.percentile(nir_data, 25)
        nir_upper = np.percentile(nir_data, 75)
        nir_inter = (nir_low - box_scale * (nir_upper - nir_low),
                     box_scale * (nir_upper - nir_low) + nir_upper)

        ind_useful = np.where((blue_data >= blue_inter[0]) & (blue_data <= blue_inter[1]) &
                              (green_data >= green_inter[0]) & (green_data <= green_inter[1]) &
                              (red_data >= red_inter[0]) & (red_data <= red_inter[1]) &
                              (red_edge_data >= red_edge_inter[0]) & (red_edge_data <= red_edge_inter[1]) &
                              (nir_data >= nir_inter[0]) & (nir_data <= nir_inter[1]))

        num_useful = len(blue_data[ind_useful])
        print(len(blue_data), num_useful)

        print(np.array(iblock_point_name)[ind_useful])

        out_csv_writer.writerow(np.array(iblock_point_name)[ind_useful].tolist())

        for iband in range(iblock_spec_array.shape[0]):
            iband_spec_array = iblock_spec_array[iband, :]
            out_csv_writer.writerow(iband_spec_array[ind_useful].tolist())

    out_csv.close()
    out_csv_writer = None




if __name__ == '__main__':

    if len(sys.argv[1:]) < 2:
        sys.exit('Problem reading input')

    in_file = sys.argv[1]
    out_file = sys.argv[2]

    # in_file =r"D:\Data\Test_data\radiation_calobration\planet_2018080811\2018080811_FS4.csv"
    # out_file = r'D:\Data\Sample_data\嵩山定标\光谱数据\201806051330_FS4_txt2csv_filter.csv'
    #
    # in_file = r"D:\Data\Test_data\radiation_calobration\planet_2018080711\2018080711_HH2.csv"
    # in_file = r"D:\Data\Test_data\radiation_calobration\planet_2018060513\201806051330_FS4_txt.csv"

    main(in_file, out_file)