#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/7/11 14:47

Description:
    将基准影像分块处理

Parameters
    in_file:待分块影像路径
    size_wind:分割窗口的大小
    num_pixel:输出分块影像的像素数目
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


    tif_files = in_list[:-3]
    model_file = in_list[-3]
    out_dir = in_list[-2]
    size_wind = in_list[-1]

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

            if np.min(in_data[0, (iyoffset + num_sub_size):(iyoffset + num_sub_size + 1),
               (ixoffset + num_sub_size):(ixoffset + num_sub_size + 1)]) > 0:

                isample_data = in_data[:, iyoffset:(iyoffset + size_wind), ixoffset:(ixoffset + size_wind)]

                out_csv_writer.writerow([iyoffset+yoffset, ixoffset+xoffset] + isample_data.T.flatten().tolist())

            # temp_data = np.vstack((temp_data, isample_data.T.flatten()))
            # xind_list.append(iyoffset)
            # yind_list.append(ixoffset)

            isample_data = None

    out_csv.close()
    out_csv_writer = None

def block_raster(in_file, temp_dir, num_pixel, size_wind):

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

    num_xblock = int(num_pixel / ysize)

    for xoffset in range(0, xsize, num_xblock):
        if xoffset + num_xblock < xsize:
            num_xsize = num_xblock
        else:
            num_xsize = xsize - xoffset

        resahpe_file = os.path.join(temp_dir, '%d_%d_%d_%d.tif' % (xoffset, 0, num_xsize, ysize))

        # 设置输出影像
        out_driver = gdal.GetDriverByName('GTiff')

        if os.path.exists(resahpe_file):
            out_driver.Delete(resahpe_file)
        reshape_dataset = out_driver.Create(resahpe_file, num_xsize + 2 * num_sub_size, ysize + 2 * num_sub_size, num_band,
                                            data_type)

        for iband in range(num_band):
            in_band = source_dataset.GetRasterBand(1 + iband)

            out_band = reshape_dataset.GetRasterBand(1 + iband)
            out_band.Fill(0)

            if xoffset == 0:

                if num_xsize + num_sub_size < xsize:

                    in_data = in_band.ReadAsArray(xoffset, 0, num_xsize + num_sub_size, ysize)
                else:
                    in_data = in_band.ReadAsArray(xoffset, 0, xsize, ysize)
                out_band.WriteArray(in_data, num_sub_size, num_sub_size)
            else:

                if xoffset + num_xsize + num_sub_size < xsize:

                    in_data = in_band.ReadAsArray(xoffset - num_sub_size, 0, num_xsize + num_sub_size, ysize)
                else:
                    in_data = in_band.ReadAsArray(xoffset - num_sub_size, 0, xsize - xoffset, ysize)
                out_band.WriteArray(in_data, 0, num_sub_size)



            in_data = None
            in_band = None
            out_band = None
        reshape_dataset = None
    source_dataset = None


def main(in_file, size_wind, num_pixel, out_dir):


    # 新建缓存文件夹
    rand_str = ''.join(random.sample(string.ascii_letters + string.digits, 4))
    temp_dir = os.path.join(tempfile.gettempdir(), 'gdal_%s' % rand_str)
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    os.mkdir(temp_dir)

    block_raster(in_file, temp_dir, num_pixel, size_wind)

    tif_files = search_file(temp_dir, '.tif')

    if tif_files == []:
        sys.exit('no file')

    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.mkdir(out_dir)

    num_proc = int(mp.cpu_count() * 1 / 2)
    pool = mp.Pool(processes=num_proc)

    block_num_file = int(len(tif_files) / num_proc)

    for iproc in range(num_proc):

        if iproc == (num_proc - 1):
            sub_in_files = tif_files[(iproc * block_num_file):]
        else:
            sub_in_files = tif_files[(iproc * block_num_file): (iproc * block_num_file) + block_num_file]

        in_list = sub_in_files + [num_pixel, out_dir, size_wind]

        pool.apply_async(run_classification_model, args=(in_list, ))

        progress(iproc / num_proc)

    pool.close()
    pool.join()

    # source_dataset = gdal.Open(in_file)
    #
    # if source_dataset is None:
    #     sys.exit('Problem opening file %s!' % in_file)
    #
    # xsize = source_dataset.RasterXSize
    # ysize = source_dataset.RasterYSize
    # num_band = source_dataset.RasterCount
    # geotransform = source_dataset.GetGeoTransform()
    # projection = source_dataset.GetProjectionRef()
    # data_type = source_dataset.GetRasterBand(1).DataType
    #
    # num_sub_size = int(size_wind / 2)
    #
    # resahpe_file = os.path.join(temp_dir, '%s_reshape.tif' % (os.path.splitext(os.path.basename(in_file))[0]))
    #
    # # 设置输出影像
    # out_driver = gdal.GetDriverByName('GTiff')
    #
    # if os.path.exists(resahpe_file):
    #     out_driver.Delete(resahpe_file)
    # reshape_dataset = out_driver.Create(resahpe_file, xsize + 2 * num_sub_size, ysize + 2 * num_sub_size, num_band,
    #                                     data_type)
    #
    # for iband in range(num_band):
    #     in_band = source_dataset.GetRasterBand(1 + iband)
    #
    #     in_data = in_band.ReadAsArray(0, 0, xsize, ysize)
    #     out_band = reshape_dataset.GetRasterBand(1 + iband)
    #     out_band.Fill(0)
    #     out_band.WriteArray(in_data, num_sub_size, num_sub_size)
    #
    #     in_data = None
    #     in_band = None
    #     out_band = None
    #
    # # 对扩增影像分块
    # re_ysize = ysize + 2 * num_sub_size
    # # num_xblock = 1000
    #
    #
    # out_tif_list = []
    #
    #
    #
    #
    # num_xblock = int(num_pixel / ysize)
    #
    # for xoffset in range(0, xsize, num_xblock):
    #     if xoffset + num_xblock < xsize:
    #         num_xsize = num_xblock
    #     else:
    #         num_xsize = xsize - xoffset
    #
    #
    #     if xoffset == 0:
    #
    #         block_data = reshape_dataset.ReadAsArray(0, 0, num_xsize + 2 * num_sub_size, re_ysize)
    #     else:
    #         block_data = reshape_dataset.ReadAsArray(xoffset, 0, num_xsize + 2 * num_sub_size, re_ysize)
    #
    #
    #     iout_file = os.path.join(out_dir, '%s_%d_%d_%d_%d.csv'
    #                              % (
    #                                  (os.path.splitext(os.path.basename(resahpe_file)))[0], xoffset, 0, num_xsize,
    #                                  ysize))
    #     if os.path.exists(iout_file):
    #         os.remove(iout_file)
    #
    #     run_jit(block_data, np.array([xoffset, 0, num_xsize, ysize, size_wind]), iout_file)
    #
    #     out_tif_list.append(iout_file)
    #
    #     progress((xoffset+num_xblock) / xsize)
    # reshape_dataset = None
    # source_dataset = None
    #
    # # # linux系统中分文件夹存储
    # # sys_str = platform.system()
    # # if (sys_str == 'Linux'):
    # #     block_num_file = int(len(out_tif_list) / 4)
    # #     num_dir = 4
    # #
    # #     for idir in range(num_dir):
    # #         iblock_dir = os.path.join(out_dir, '%d' % idir)
    # #         if os.path.exists(iblock_dir):
    # #             shutil.rmtree(iblock_dir)
    # #         os.mkdir(iblock_dir)
    # #
    # #         if idir == 3:
    # #             sub_out_list = out_tif_list[(idir * block_num_file):]
    # #         else:
    # #             sub_out_list = out_tif_list[(idir * block_num_file): (idir * block_num_file) + block_num_file]
    # #
    # #         for iout_file in sub_out_list:
    # #             shutil.move(iout_file, iblock_dir)
    # #
    # #
    shutil.rmtree(temp_dir)
    progress(1)


if __name__ == '__main__':
    start_time = time.time()

    if len(sys.argv[1:]) < 4:
        sys.exit('Problem reading input')
    #
    main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
    # in_file = r"D:\Data\Test_data\classification\20180810\GF2_20180327_S2_0309_0324_0408_clip_sub.tif"
    # out_dir = r'D:\Data\Test_data\classification\20180810\test_csv4'
    # size_wind = 7
    # num_sample = 500000
    # main(in_file, size_wind, num_sample, out_dir)


    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))