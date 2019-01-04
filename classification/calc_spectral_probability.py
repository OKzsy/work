#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/3/29 9:30

Description:


Parameters


"""
import os
import sys
import time
import csv
import random
import string
import platform
import tempfile
import shutil
import subprocess
import numpy as np
import numba as nb
import pandas as pd

try:
    from osgeo import gdal
except ImportError:
    import gdal

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


@nb.jit
def calc_prob(w, o):
    cos = np.dot(w, o) / (np.linalg.norm(w) * np.linalg.norm(o))  # 向量夹角
    n = w.shape[0]
    dist = 1 - (np.linalg.norm(w - o) / np.sqrt(n))  # 距离
    p = cos * dist
    return p


@nb.jit
def get_prob(in_data, standard_array):
    # 读取csv

    # in_csv = open(in_file, 'r')

    # yancao_standard_spec = np.array([1283.551196, 1596.477376, 1724.206287, 2697.742535,
    #                                  1758.066113, 2150.967404, 2559.851084, 4407.301452])
    #
    # xiaomai_standard_spec = np.array([493.462183, 719.7352203, 788.5917242, 1913.691412,
    #                                   944.5644721, 1166.320235, 1599.986156, 2258.447358])
    ysize = in_data.shape[1]
    xsize = in_data.shape[2]

    num_flag = standard_array.shape[0]
    flag_p = np.empty((ysize, xsize, num_flag), dtype=np.int16)
    flag_p[:, :, :] = 10000

    # xiaomai_p = np.empty((ysize, xsize), dtype=np.float32)
    # xiaomai_p[:, :] = 1.0
    # 写入csv
    # out_csv = open(out_file, 'w', newline='')
    # out_csv_writer = csv.writer(out_csv)

    for iyoffset in range(ysize):
        for ixoffset in range(xsize):

            if in_data[0, iyoffset, ixoffset] <= 0:
                continue

            isample_data = in_data[:, iyoffset, ixoffset] * 1.0

            for iflag in range(num_flag):
                flag_p[iyoffset, ixoffset, iflag] = int(calc_prob(isample_data / 10000, standard_array[iflag, :] / 10000) * 10000)

            # yancao_p[iyoffset, ixoffset] = calc_prob(isample_data / 10000, yancao_standard_spec / 10000)
            # xiaomai_p[iyoffset, ixoffset] = calc_prob(isample_data / 10000, xiaomai_standard_spec / 10000)

            # temp_data = np.vstack((temp_data, isample_data.T.flatten()))
            # xind_list.append(iyoffset)
            # yind_list.append(ixoffset)

            isample_data = None
        # print(iyoffset / )

    return flag_p


def read_csv(in_file):
    csv_shape = pd.read_csv(in_file, header=None, nrows=1).shape

    out_data = np.zeros((csv_shape[0], csv_shape[1]), dtype=np.float)

    chunksize = 10 ** 6
    for chunk in pd.read_csv(in_file, header=None, chunksize=chunksize):
        out_data = np.vstack((out_data, chunk.values))
        chunk = None

    return out_data[1:, :]


@nb.jit
def calc_mean(flag, in_file):
    csv_data = read_csv(in_file)
    ind_data = np.zeros((csv_data.shape[0], csv_data.shape[1]), dtype=np.byte)

    band_range = []
    box_scale = 1.5
    for iband in range(csv_data.shape[1]):
        band_data = csv_data[:, iband]

        band_low = np.percentile(band_data, 25)
        band_upper = np.percentile(band_data, 75)
        band_inter = (band_low - box_scale * (band_upper - band_low),
                      box_scale * (band_upper - band_low) + band_upper)

        ind_useful = np.where((band_data >= band_inter[0]) & (band_data <= band_inter[1]))
        ind_data[:, iband][ind_useful] = 1

        band_range.append(band_inter)

    use_ind = []
    imean_array = np.zeros((ind_data.shape[1]), np.float)
    imax_array = csv_data[0, :].astype(np.float)
    imin_array = csv_data[0, :].astype(np.float)

    for isample in range(ind_data.shape[0]):
        isample_ind = ind_data[isample, :]

        if np.all(isample_ind == np.ones((ind_data.shape[1]), dtype=np.byte)):
            use_ind.append(isample)
            isample_data = csv_data[isample, :]

            imax_array = np.maximum(imax_array, csv_data[isample, :])
            imin_array = np.minimum(imin_array, csv_data[isample, :])

            # for iband in range(len(isample_data)):
            #     if imax_array[iband]
            imean_array = imean_array + csv_data[isample, :]

            # print('ok')
        else:
            # print('no')
            continue
    print(flag, csv_data.shape[0], len(use_ind), int(len(use_ind) / csv_data.shape[0] * 100))

    return imean_array / len(use_ind), imax_array, imin_array


@nb.jit
def get_spec(in_data, out_file):
    ysize = in_data.shape[1]
    xsize = in_data.shape[2]

    # 写入csv
    out_csv = open(out_file, 'w', newline='')
    out_csv_writer = csv.writer(out_csv)

    for iyoffset in range(ysize):
        for ixoffset in range(xsize):

            if in_data[0, iyoffset, ixoffset] <= 0:
                continue

            isample_data = in_data[:, iyoffset, ixoffset]

            out_csv_writer.writerow(isample_data.flatten().tolist())

            # temp_data = np.vstack((temp_data, isample_data.T.flatten()))
            # xind_list.append(iyoffset)
            # yind_list.append(ixoffset)

            isample_data = None

    out_csv.close()
    out_csv_writer = None


def search_file(folder_path, file_extension):
    flag = []
    search_files = []
    for dir_path, dir_names, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(file_extension):
                flag.append(os.path.splitext(file)[0].split('-')[-1])
                search_files.append(os.path.normpath(os.path.join(dir_path, file)))

    flag_set = list(set(flag))
    flag_set.sort(key=flag.index)
    out_dict = {}
    for iflag in flag_set:

        iflag_list = []
        for ifile in search_files:
            file_flag = os.path.splitext(ifile)[0].split('-')[-1]
            if file_flag == iflag:
                iflag_list.append(ifile)
        out_dict[iflag] = iflag_list
    return out_dict


def img2prob(in_file, standard_spec, out_file):

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
    out_dataset = out_driver.Create(out_file, xsize, ysize, standard_spec.shape[0], gdal.GDT_Int16)


    num_xblock = 5000

    for xoffset in range(0, xsize, num_xblock):
        if xoffset + num_xblock < xsize:
            num_xsize = num_xblock
        else:
            num_xsize = xsize - xoffset

        block_data = source_dataset.ReadAsArray(xoffset, 0, num_xsize, ysize)

        flag_p = get_prob(block_data, standard_spec)

        block_data = None

        for iband in range(standard_spec.shape[0]):
            out_band = out_dataset.GetRasterBand(1 + iband)

            out_band.WriteArray(flag_p[:, :, iband].reshape(ysize, num_xsize), 0, 0)

        flag_p = None

    out_dataset.SetGeoTransform(geotransform)
    out_dataset.SetProjection(projection)
    out_dataset = None
    source_dataset = None

def read_raster(in_file):
    source_dataset = gdal.Open(in_file)

    if source_dataset is None:
        sys.exit('Problem opening file %s!' % in_file)

    xsize = source_dataset.RasterXSize
    ysize = source_dataset.RasterYSize
    num_band = source_dataset.RasterCount
    geotransform = source_dataset.GetGeoTransform()
    projection = source_dataset.GetProjectionRef()
    data_type = source_dataset.GetRasterBand(1).DataType

    in_data = source_dataset.ReadAsArray(0, 0, xsize, ysize)
    source_dataset  = None

    return in_data
def main():
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)

    os.mkdir(out_dir)
    sys_str = platform.system()
    in_dict = search_file(in_dir, 'tif')
    flag_list = list(in_dict.keys())

    # 写入csv
    out_csv = open(out_csv_file, 'w', newline='')
    out_csv_writer = csv.writer(out_csv)

    #
    standard_spec = []
    for iflag in flag_list:
        flag_files = in_dict[iflag]

        flag_dir = os.path.join(out_dir, '%s' % iflag)
        if os.path.exists(flag_dir):
            shutil.rmtree(flag_dir)

        os.mkdir(flag_dir)

        for iflag_file in flag_files:
            iout_file = os.path.join(flag_dir, '%s.csv'
                                     % (os.path.splitext(os.path.basename(iflag_file)))[0])




            get_spec(read_raster(iflag_file), iout_file)

        out_file = os.path.join(out_dir, '%s.csv' % iflag)
        if (sys_str == 'Windows'):

            cmd_str = r'copy /b *.csv %s' % (out_file)
            # 不打印列表
            # subprocess.call(cmd_str, shell=True, stdout=open(os.devnull, 'w'), cwd=flag_dir)

        elif (sys_str == 'Linux'):
            cmd_str = r'cat *.csv > %s' % (out_file)

        else:
            sys.exit('no system platform')

        # 不打印列表
        subprocess.call(cmd_str, shell=True, stdout=open(os.devnull, 'w'), cwd=flag_dir)
        mean_array, max_array, min_array = calc_mean(iflag, out_file)

        out_csv_writer.writerow(['%s_mean' % iflag] + mean_array.flatten().tolist())
        standard_spec.append(mean_array.flatten())
        # out_csv_writer.writerow(['%s_max' % iflag] + max_array.flatten().tolist())
        # out_csv_writer.writerow(['%s_min' % iflag] + min_array.flatten().tolist())
    out_csv.close()
    out_csv_writer = None


    img2prob(in_file, np.array(standard_spec), out_p_file)

    print()



if __name__ == '__main__':
    start_time = time.time()

    in_file = r"D:\Data\Test_data\classification\20180804\GF2_20180327_S2_0309_0324_0408_0418tif.tif"

    in_dir = r'D:\Data\Test_data\classification\20180804\sample_tif'
    out_dir = r'D:\Data\Test_data\classification\20180804\sample_csv'
    out_csv_file = r'D:\Data\Test_data\classification\20180804\sample_csv_mean.csv'

    out_p_file = r"D:\Data\Test_data\classification\20180804\GF2_20180327_S2_0309_0324_0408_0418tif_p.tif"
    main()

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))