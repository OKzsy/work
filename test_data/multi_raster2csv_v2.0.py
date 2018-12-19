#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/8/25 16:14

Description:
    将基准影像分块处理

Parameters
    in_file:待分块影像路径
    size_wind:分割窗口的大小
    out_dir:输出分块影像的文件夹路径


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
import numpy as np
import numba as nb
import multiprocessing as mp

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


def run_classification_model(in_list):


    tif_files = in_list[0]
    model_file = in_list[1]
    out_dir = in_list[2]
    size_wind = in_list[3]

    for tif_file in tif_files:

        file_names = os.path.splitext(os.path.basename(tif_file))[0].split('_')

        file_names = [int(i) for i in file_names]
        file_names.append(size_wind)

        iout_file = os.path.join(out_dir, '%s.csv'
                                 % os.path.splitext(os.path.basename(tif_file))[0])


        source_dataset = gdal.Open(tif_file)

        if source_dataset is None:
            sys.exit('Problem opening file %s!' % tif_file)

        tif_xsize = source_dataset.RasterXSize
        tif_ysize = source_dataset.RasterYSize

        block_data = source_dataset.ReadAsArray(0, 0, tif_xsize, tif_ysize)


        run_jit(block_data, file_names, iout_file)

        source_dataset = None
        block_data = None

@nb.jit
def run_jit(in_data, in_array, out_file):

    xoffset = in_array[0]
    yoffset = in_array[1]
    num_xsize = in_array[2]
    ysize = in_array[3]
    size_wind = in_array[4]

    num_sub_size = int(size_wind / 2)
    # temp_data = np.zeros((1, size_wind, size_wind, num_band), dtype=np.int16)
    # temp_data = np.zeros((1, size_wind*size_wind*num_band), dtype=np.int16)

    # temp_data = np.empty((1, size_wind*size_wind*num_band), dtype=np.int16)
    # xind_list = []
    # yind_list = []
    # 写入csv
    out_csv = open(out_file, 'w', newline='')
    out_csv_writer = csv.writer(out_csv)

    for iyoffset in range(ysize):
        for ixoffset in range(num_xsize):

            # print(in_data[:, (iyoffset + num_sub_size), (ixoffset + num_sub_size)].flatten()[0])

            if in_data[:, (iyoffset + num_sub_size), (ixoffset + num_sub_size)].flatten()[0] > 0:

                isample_data = in_data[:, iyoffset:(iyoffset + size_wind), ixoffset:(ixoffset + size_wind)]

                out_csv_writer.writerow([iyoffset+yoffset, ixoffset+xoffset] + isample_data.T.flatten().tolist())

            # temp_data = np.vstack((temp_data, isample_data.T.flatten()))
            # xind_list.append(iyoffset)
            # yind_list.append(ixoffset)

            isample_data = None

    out_csv.close()
    out_csv_writer = None

def block_raster(in_file, temp_dir, size_wind):

    num_sub_size = int(size_wind / 2)

    source_dataset = gdal.Open(in_file)

    if source_dataset is None:
        sys.exit('Problem opening file %s!' % in_file)

    xsize = source_dataset.RasterXSize
    ysize = source_dataset.RasterYSize
    num_band = source_dataset.RasterCount
    geotransform = source_dataset.GetGeoTransform()
    projection = source_dataset.GetProjectionRef()
    data_type = source_dataset.GetRasterBand(1).DataType

    num_xblock = 100

    for xoffset in range(0, xsize, num_xblock):
        if xoffset + num_xblock < xsize:
            num_xsize = num_xblock
        else:
            num_xsize = xsize - xoffset


        # 设置输出影像
        reshape_file = os.path.join(temp_dir, '%d_%d_%d_%d.tif' % (xoffset, 0, num_xsize, ysize))
        out_driver = gdal.GetDriverByName('GTiff')
        if os.path.exists(reshape_file):
            out_driver.Delete(reshape_file)
        reshape_dataset = out_driver.Create(reshape_file, num_xsize + 2 * num_sub_size, ysize + 2 * num_sub_size, num_band,
                                            data_type)

        for iband in range(num_band):
            in_band = source_dataset.GetRasterBand(1 + iband)
            out_band = reshape_dataset.GetRasterBand(1 + iband)
            out_band.Fill(0)

            if xoffset == 0:
                if num_xsize + num_sub_size < xsize:
                    in_data = in_band.ReadAsArray(xoffset, 0, num_xsize + num_sub_size, ysize)
                    # print(0)
                else:
                    in_data = in_band.ReadAsArray(xoffset, 0, xsize, ysize)
                    # print(1)
                out_band.WriteArray(in_data, num_sub_size, num_sub_size)
            else:
                if xoffset + num_xsize + num_sub_size < xsize:
                    in_data = in_band.ReadAsArray(xoffset - num_sub_size, 0, num_xsize + 2*num_sub_size, ysize)
                    # print(2)
                else:
                    in_data = in_band.ReadAsArray(xoffset - num_sub_size, 0, xsize - xoffset, ysize)
                    # print(3)
                out_band.WriteArray(in_data, 0, num_sub_size)

            in_data = None
            in_band = None
            out_band = None
        reshape_dataset = None
    source_dataset = None

def main(in_file, size_wind, out_dir):

    # 新建缓存文件夹
    sys_str = platform.system()
    if (sys_str == 'Windows'):
        temp_dir = os.path.join(tempfile.gettempdir(), 'gdal_temp')
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.mkdir(temp_dir)
    else:
        rand_str = ''.join(random.sample(string.ascii_letters + string.digits, 4))
        temp_dir = os.path.join(tempfile.gettempdir(), 'gdal_%s' % rand_str)
        if not os.path.exists(temp_dir):
            os.mkdir(temp_dir)

    block_raster(in_file, temp_dir, size_wind)

    tif_files = search_file(temp_dir, '.tif')

    if tif_files == []:
        sys.exit('no file')

    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.mkdir(out_dir)

    num_proc = int(mp.cpu_count() * 1 / 2)
    num_proc = int(mp.cpu_count() - 1)
    if len(tif_files) < num_proc:
        num_proc = len(tif_files)
        block_num_file = 1
    else:
        block_num_file = int(len(tif_files) / num_proc)

    pool = mp.Pool(processes=num_proc)
    for iproc in range(num_proc):

        if iproc == (num_proc - 1):
            sub_in_files = tif_files[(iproc * block_num_file):]
        else:
            sub_in_files = tif_files[(iproc * block_num_file): (iproc * block_num_file) + block_num_file]

        in_list = [sub_in_files, '', out_dir, size_wind]

        pool.apply_async(run_classification_model, args=(in_list, ))

        progress(iproc / num_proc)

    pool.close()
    pool.join()


    shutil.rmtree(temp_dir)
    progress(1)


if __name__ == '__main__':
    start_time = time.time()

    if len(sys.argv[1:]) < 3:
        sys.exit('Problem reading input')
    main(sys.argv[1], int(sys.argv[2]), sys.argv[3])
    # in_file = r"D:\Data\Test_data\classification\20180825\GF2_20180327_S20324_sanguanmiao.tif"
    # size_wind = 7
    # out_dir = r"D:\Data\Test_data\classification\20180825\test_csv_2"
    # main(in_file, size_wind, out_dir)

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))