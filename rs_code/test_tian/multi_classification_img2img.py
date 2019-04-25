#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/12/26 17:59

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
import multiprocessing as mp
import numba as nb
import numpy as np
import queue
try:
    from osgeo import gdal
except ImportError:
    import gdal

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress

@nb.jit
def run_jit(in_data, in_array):

    xoffset = in_array[0]
    yoffset = in_array[1]
    num_xsize = in_array[2]
    ysize = in_array[3]
    size_wind = in_array[4]

    num_sub_size = int(size_wind / 2)

    out_data = []
    for iyoffset in range(ysize):
        for ixoffset in range(num_xsize):
            if in_data[:, (iyoffset + num_sub_size), (ixoffset + num_sub_size)].flatten()[0] > 0:

                isample_data = in_data[:, iyoffset:(iyoffset + size_wind), ixoffset:(ixoffset + size_wind)]
                out_data.append(np.array([iyoffset+yoffset, ixoffset+xoffset] + isample_data.T.flatten().tolist()))
                isample_data = None
    return np.array(out_data)


def array2array(in_list):


    in_array = in_list[0]
    block_list = in_list[1]
    model = in_list[2]
    size_wind = in_list[3]
    lock = in_list[4]

    num_sub_size = int(size_wind / 2.0)

    if len(in_array.shape) == 2:
        num_band = 1
        ysize, xsize = in_array.shape
    else:
        num_band, ysize, xsize = in_array.shape

    o_data = np.zeros((ysize, xsize), dtype=np.uint8)
    o_data[:, :] = 200

    xind = []
    yind = []

    for iblock in range(len(block_list)):
        xoffset, yoffset, num_xsize, ysize = block_list[iblock]

        in_data = np.zeros((num_band, ysize + 2 * num_sub_size, num_xsize + 2 * num_sub_size), dtype=np.int16)
        # 根据不同的边界条件截取数组
        if xoffset == 0:
            if xoffset + num_xsize + num_sub_size < xsize:
                in_data[:, num_sub_size:ysize + num_sub_size, num_sub_size:] = \
                    in_array[:, :, xoffset:xoffset + num_xsize + num_sub_size]
            else:
                in_data[:, num_sub_size:ysize + num_sub_size, num_sub_size:xsize + num_sub_size] = \
                    in_array[:, :, xoffset:xoffset + xsize]
        else:
            if xoffset + num_xsize + num_sub_size < xsize:
                in_data[:, num_sub_size:ysize + num_sub_size, :] = \
                    in_array[:, :, xoffset - num_sub_size:xoffset + num_xsize + num_sub_size]
            else:
                in_data[:, num_sub_size:ysize + num_sub_size, num_sub_size:num_xsize + num_sub_size] = \
                    in_array[:, :, xoffset - num_sub_size:xsize - num_sub_size]

        out_data = run_jit(in_data, [xoffset, xoffset, num_xsize, ysize, size_wind])

        # 如果没有合格的数组则跳过
        if len(out_data) == 0:
            continue

        num_band = int(out_data[:, 2:].shape[1] / (size_wind ** 2))
        y_pred = model.predict_classes(out_data[:, 2:].reshape(out_data[:, 2:].shape[0], size_wind, size_wind, num_band)
                                       / 10000.0)

        for iout in range(out_data.shape[0]):
            o_data[out_data[iout, :][0], out_data[iout, :][1]] = y_pred[iout]

        out_data = None
        y_pred = None
        in_data = None
        in_data = None

    return o_data


def multi_array2array(in_array, block_list, model_file, size_wind):

    from keras.models import load_model
    import tensorflow as tf
    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True
    session = tf.Session(config=config)

    model = load_model(model_file)

    if len(in_array.shape) == 2:
        num_band = 1
        ysize, xsize = in_array.shape
    else:
        num_band, ysize, xsize = in_array.shape


    # 新建填充值为200的数组
    o_data = np.empty((ysize, xsize), dtype=np.uint8)
    o_data[:, :] = 200

    num_proc = int(mp.cpu_count() - 1)

    if len(block_list) < num_proc:
        num_proc = len(block_list)
        block_num_file = 1
    else:
        block_num_file = int(len(block_list) / num_proc)

    pool = mp.Pool(processes=num_proc)

    results = []
    for iproc in range(num_proc):

        if iproc == (num_proc - 1):
            sub_in_files = block_list[(iproc * block_num_file):]
        else:
            sub_in_files = block_list[(iproc * block_num_file): (iproc * block_num_file) + block_num_file]

        # print(len(sub_in_files))


        in_list = [in_array, sub_in_files, model, size_wind, o_data]
        # io_data = array2array(in_list)
        # o_data[io_data != 200] = io_data[io_data != 200]

        results.append(pool.apply_async(array2array, args=(in_list,)))

        # progress(iproc / num_proc)

    pool.close()
    pool.join()

    for r in results:
        io_data = r.get()
        o_data[io_data != 200] = io_data[io_data != 200]

    session.close()

    return o_data



def main(in_file, size_wind, model_file, out_file):

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
    block_list = []
    for xoffset in range(0, xsize, num_xblock):
        if xoffset + num_xblock < xsize:
            num_xsize = num_xblock
        else:
            num_xsize = xsize - xoffset
        block_list.append([xoffset, 0, num_xsize, ysize])


    # 设置输出影像
    out_driver = gdal.GetDriverByName('GTiff')

    if os.path.exists(out_file):
        out_driver.Delete(out_file)
    out_dataset = out_driver.Create(out_file, xsize, ysize, 1, gdal.GDT_Byte)
    out_band = out_dataset.GetRasterBand(1)

    o_data =  multi_array2array(source_dataset.ReadAsArray(), block_list, model_file, size_wind)


    out_band.WriteArray(o_data ,0, 0)

    out_dataset.SetGeoTransform(geotransform)
    out_dataset.SetProjection(projection)

    source_dataset = None
    out_dataset = None
    out_band = None

    # print(out_data[0, :])


if __name__ == '__main__':
    start_time = time.time()
    #
    # if len(sys.argv[1:]) < 2:
    #     sys.exit('Problem reading input')
    # main(sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4])
    in_file = r"\\192.168.0.234\nydsj\user\TJG\classification\20181226\gongyi_12band_sub_sub.tif"
    size_wind = 7
    model_file = r"\\192.168.0.234\nydsj\user\TJG\classification\20181226\cnn1_patch_model.h5"
    out_file = r"\\192.168.0.234\nydsj\user\TJG\classification\20181226\gongyi_12band_sub_sub_c3.tif"
    main(in_file, size_wind , model_file, out_file)

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))