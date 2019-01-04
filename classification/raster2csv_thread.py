#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/6/26 20:32

Description:


Parameters


"""

import os
import sys
import time
import tempfile
import shutil
import numpy as np
import operator
import pandas as pd
from multiprocessing import Process
from multiprocessing import cpu_count

try:
    from osgeo import gdal
except ImportError:
    import gdal
from tensorflow.contrib.keras.api.keras.models import load_model

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


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


def search_file(folder_path, file_extension):
    search_files = {}
    for dirpath, dirnames, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(file_extension):
                size_raster = os.path.splitext(file)[0].split('_')[-4:]
                search_files[int(size_raster[0])] = (os.path.normpath(os.path.join(dirpath, file)))
    return search_files



def reshape_raster(in_file, size_wind, num_sample, out_dir):
    source_dataset = gdal.Open(in_file)

    if source_dataset is None:
        sys.exit('Problem opening file %s!' % in_file)

    xsize = source_dataset.RasterXSize
    ysize = source_dataset.RasterYSize
    num_band = source_dataset.RasterCount
    geotransform = source_dataset.GetGeoTransform()
    projection = source_dataset.GetProjectionRef()
    data_type = source_dataset.GetRasterBand(1).DataType

    num_sub_size = int(size_wind / 2)

    resahpe_file = os.path.join(out_dir, '%s_reshape.tif' % (os.path.splitext(os.path.basename(in_file))[0]))

    # 设置输出影像
    out_driver = gdal.GetDriverByName('GTiff')

    if os.path.exists(resahpe_file):
        out_driver.Delete(resahpe_file)
    reshape_dataset = out_driver.Create(resahpe_file, xsize + 2 * num_sub_size, ysize + 2 * num_sub_size, num_band,
                                        data_type)

    for iband in range(num_band):
        in_band = source_dataset.GetRasterBand(1 + iband)

        in_data = in_band.ReadAsArray(0, 0, xsize, ysize)
        out_band = reshape_dataset.GetRasterBand(1 + iband)
        out_band.Fill(0)
        out_band.WriteArray(in_data, num_sub_size, num_sub_size)

        in_data = None
        in_band = None
        out_band = None

    # 对扩增影像分块
    re_ysize = ysize + 2 * num_sub_size
    # num_xblock = 1000
    temp_dir = os.path.join(out_dir, 'block_tif')

    if not os.path.isdir(temp_dir):
        os.mkdir(temp_dir)

    num_xblock = int(num_sample / ysize)

    for xoffset in range(0, xsize, num_xblock):
        if xoffset + num_xblock < xsize:
            num_xsize = num_xblock
        else:
            num_xsize = xsize - xoffset

        temp_data = np.zeros((1, size_wind, size_wind, num_band), dtype=np.float)

        if xoffset == 0:

            block_data = reshape_dataset.ReadAsArray(0, 0, num_xsize + 2 * num_sub_size, re_ysize)
        else:
            block_data = reshape_dataset.ReadAsArray(xoffset, 0, num_xsize + 2 * num_sub_size, re_ysize)

        print(xoffset, num_xsize)

        iout_file = os.path.join(temp_dir, '%s_%d_%d_%d_%d.tif'
                                 % (
                                     (os.path.splitext(os.path.basename(resahpe_file)))[0], xoffset, 0, num_xsize,
                                     ysize))
        if os.path.exists(iout_file):
            out_driver.Delete(iout_file)

        out_dataset = out_driver.Create(iout_file, num_xsize + 2 * num_sub_size, re_ysize, num_band, data_type)

        for iband in range(num_band):
            iout_band = out_dataset.GetRasterBand(iband + 1)
            iout_band.WriteArray(block_data[iband, :, :], 0, 0)
            iout_band = None

        out_dataset = None
        block_data = None

    reshape_dataset = None
    source_dataset = None
    return temp_dir, geotransform, projection


def class_raster(in_list, model_file, size_wind, class_block_dir):

    out_driver = gdal.GetDriverByName('GTiff')

    for isub_tif in in_list:

        isub_filename = os.path.splitext(os.path.basename(list(isub_tif)[1]))[0]
        iclass_out_file = os.path.join(class_block_dir, '%s_class.tif' % isub_filename)

        if os.path.exists(iclass_out_file):
            out_driver.Delete(iclass_out_file)

        file_name = os.path.splitext(os.path.basename(list(isub_tif)[1]))[0].split('_')[-4:]
        ysize = int(file_name[3])
        num_xsize = int(file_name[2])
        num_sub_size = int(size_wind / 2)

        sds = gdal.Open(list(isub_tif)[1])
        if sds is None:
            sys.exit('Problem opening file %s!' % list(isub_tif)[1])

        sds_xsize = sds.RasterXSize
        sds_ysize = sds.RasterYSize
        num_band = sds.RasterCount

        in_data = sds.ReadAsArray(0, 0, sds_xsize, sds_ysize)
        temp_data = np.zeros((1, size_wind, size_wind, num_band), dtype=np.float)
        xind_list = []
        yind_list = []

        out_dataset = out_driver.Create(iclass_out_file, num_xsize, ysize, 1, gdal.GDT_Byte)
        out_band = out_dataset.GetRasterBand(1)

        out_data = np.zeros((ysize, num_xsize), dtype=np.uint8)
        out_data[:, :] = 200

        for iyoffset in range(ysize):
            for ixoffset in range(num_xsize):

                if in_data[0, (iyoffset + num_sub_size):(iyoffset + num_sub_size + 1),
                   (ixoffset + num_sub_size):(ixoffset + num_sub_size + 1)][0][0] <= 0:
                    continue

                isample_data = in_data[:, iyoffset:(iyoffset + size_wind), ixoffset:(ixoffset + size_wind)]
                # print(isample_data.shape)

                # is_t = isample_data.T
                # is_t_r = is_t.reshape(1, size_wind, size_wind, num_band).reshape(size_wind, size_wind, num_band)
                temp_data = np.vstack((temp_data, isample_data.T.reshape(1, size_wind, size_wind, num_band)))
                xind_list.append(iyoffset)
                yind_list.append(ixoffset)

                isample_data = None

        model = load_model(model_file)
        y_pred = model.predict_classes(temp_data[1:, :, :, :] / 10000)

        for iout in range(len(xind_list)):
            out_data[xind_list[iout], yind_list[iout]] = y_pred[iout]

        out_band.WriteArray(out_data, 0, 0)
        temp_data = None
        out_data = None
        out_band = None
        out_dataset = None
        sds = None


def main(in_file, size_wind, model_file, num_sample, out_dir):

    # 新建缓存文件夹
    temp_dir = os.path.join(tempfile.gettempdir(), 'temp_gdal')
    if not os.path.isdir(temp_dir):
        os.mkdir(temp_dir)

    # num_sample = 100000

    block_dir, geotransform, projection = reshape_raster(in_file, size_wind, num_sample, temp_dir)

    tif_dict = search_file(block_dir, '.tif')

    # 按照序号排序
    tif_list = sorted(tif_dict.items(), key=operator.itemgetter(0), reverse=False)

    # class_block_dir = os.path.join(temp_dir, 'class_block')
    class_block_dir = out_dir
    if os.path.isdir(class_block_dir):
        shutil.rmtree(class_block_dir)
        os.mkdir(class_block_dir)
    else:
        os.mkdir(class_block_dir)

    out_class_list = []

    num_proc = int(cpu_count() * 2 / 3)
    num_proc_tif = 10
    # num_proc = int(cpu_count() - 1)
    for itif in range(0, len(tif_list), num_proc * num_proc_tif):

        sub_tif_list = tif_list[itif: num_proc * num_proc_tif + itif]
        process_list = []

        for ilist in range(0, len(sub_tif_list), num_proc):
            p = Process(target=class_raster,
                        args=(sub_tif_list[ilist:ilist + num_proc_tif], model_file, size_wind, class_block_dir,))
            p.start()

            process_list.append(p)
        # out_class_list.append(iclass_out_file)

        for ip in process_list:
            ip.join()


        progress(itif / len(tif_list))
    progress(1)


if __name__ == '__main__':
    start_time = time.time()

    if len(sys.argv[1:]) < 5:
        sys.exit('Problem reading input')

    main(sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4]), sys.argv[5])

    # in_file = r"D:\Data\Test_data\un_zip\yingqiao_20180523+0607_reg_clip2.tif"
    # out_dir = r'D:\Data\Test_data\un_zip\out_dir'
    # size_wind = 7
    # num_sample = 100000
    # model_file = r"C:\Users\01\Desktop\yingqiao\model\lr\lr_0.00008\model-ep050-loss0.287-val_loss0.276-acc0.881-val_cc0.886.h5"
    # main(in_file, size_wind, model_file, num_sample, out_dir)

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))