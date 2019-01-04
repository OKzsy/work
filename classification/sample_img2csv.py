#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/7/5 19:59

Description:
    利用python多进程, 对样本影像进行切块处理,将结果输入到深度学习模型中

Parameters
    in_file:基准影像路径
    sample_dir:样本影像所在路径
    size_wind:窗口大小
    flag_file:csv标签文件所在路径
    out_file:输出csv文件路径

"""

import os
import sys
import csv
import time
import platform
import tempfile
import shutil
import random
import string
import subprocess
import numpy as np
from multiprocessing import Process
from multiprocessing import cpu_count

try:
    from osgeo import gdal
except ImportError:
    import gdal

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


# def rand_str(number_str):
#     return ''.join(random.sample(string.ascii_letters + string.digits, number_str))
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

def get_flag(flag_file):
    with open(flag_file, 'r') as in_func:
        flag_str = in_func.readlines()

    flag_dict = {}

    for iflag_str in flag_str:
        iflag_data = iflag_str.replace('\n', '').split(',')

        while '' in iflag_data:
            iflag_data.remove('')

        flag_dict[iflag_data[0]] = int(iflag_data[1])

    return flag_dict

def search_file(folder_path, file_extension):
    search_files = []
    for dir_path, dir_names, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(file_extension):
                search_files.append(os.path.normpath(os.path.join(dir_path, file)))
    return search_files

def get_sample_data(in_file, sample_file, flag_id, size_wind, out_file):

    num_sub_size = int(size_wind / 2)

    source_dataset = gdal.Open(in_file)
    if source_dataset is None:
        sys.exit('Problem opening file %s!' % in_file)

    #基准影像空间参考
    geotransform = source_dataset.GetGeoTransform()

    sample_dataset = gdal.Open(sample_file)
    if sample_dataset is None:
        sys.exit('Problem opening file %s!' % sample_file)

    sample_xsize = sample_dataset.RasterXSize
    sample_ysize = sample_dataset.RasterYSize
    sample_geotransform = sample_dataset.GetGeoTransform()
    sample_projection = sample_dataset.GetProjectionRef()

    # 样本左上角坐标
    top_left_mapx, top_Left_mapy = pixel2map(0, 0, sample_geotransform)
    # 样本右上角坐标
    top_right_mapx, top_right_mapy = pixel2map(sample_xsize, 0, sample_geotransform)
    # 样本左下角坐标
    bottom_left_mapx, bottom_left_mapy = pixel2map(0, sample_ysize, sample_geotransform)
    # 样本右下角坐标
    bottom_right_mapx, bottom_right_mapy = pixel2map(sample_xsize, sample_ysize, sample_geotransform)

    mapx_array = np.array([top_left_mapx, top_right_mapx, bottom_left_mapx, bottom_right_mapx], dtype=np.double)
    mapy_array = np.array([top_Left_mapy, top_right_mapy, bottom_left_mapy, bottom_right_mapy], dtype=np.double)

    # 样本左上角坐标在基准影像的地理坐标
    top_left_mapx_new = np.min(mapx_array)
    top_left_mapy_new = np.max(mapy_array)

    # 样本右下角坐标在基准影像的地理坐标
    bottom_right_mapx_new = np.max(mapx_array)
    bottom_right_mapy_new = np.min(mapy_array)

    # 样本左上角坐标在基准影像的直角坐标
    top_left_pixelx, top_Left_pixely = map2pixel(top_left_mapx_new, top_left_mapy_new, geotransform)
    # 样本右下角坐标在基准影像的直角坐标
    # bottom_right_pixelx, bottom_right_pixely = map2pixel(bottom_right_mapx_new, bottom_right_mapy_new, geotransform)
    bottom_right_pixelx = top_left_pixelx + sample_xsize
    bottom_right_pixely = top_Left_pixely + sample_ysize

    out_csv = open(out_file, 'w', newline='')
    out_csv_writer = csv.writer(out_csv)


    for iyoffset in range(top_Left_pixely, bottom_right_pixely, 1):
        for ixoffset in range(top_left_pixelx, bottom_right_pixelx, 1):

            data1 = source_dataset.ReadAsArray(ixoffset , iyoffset , 1, 1).flatten()

            if (top_Left_pixely < 0) or (top_left_pixelx < 0) or (bottom_right_pixely < 0) \
                or (bottom_right_pixelx < 0):
                continue
            if (source_dataset.ReadAsArray(ixoffset , iyoffset , 1, 1).flatten()[0] <= 0):
                continue

            isample_data = source_dataset.ReadAsArray(ixoffset - num_sub_size, iyoffset - num_sub_size,
                                                     size_wind, size_wind)

            isample_data_reshape = isample_data.T.flatten().tolist()
            iout_list = [ixoffset, iyoffset] + isample_data_reshape + [flag_id]
            out_csv_writer.writerow(iout_list)

            isample_data = None
            isample_data_reshape = None
            iout_list = None
    sample_dataset = None
    out_csv.close()
    out_csv_writer = None
    source_dataset = None


def main(in_file, sample_dir, flag_file, size_wind, out_file):

    # 新建缓存文件夹
    rand_str = ''.join(random.sample(string.ascii_letters + string.digits, 4))
    temp_dir = os.path.join(tempfile.gettempdir(), 'gdal_%s' % rand_str)
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    os.mkdir(temp_dir)

    flag_dict = get_flag(flag_file)

    tif_list = search_file(sample_dir, '.tif')

    # 建立多个进程
    num_proc = int(cpu_count() / 2)
    for itif in range(0, len(tif_list), num_proc):


        sub_tif_list = tif_list[itif: num_proc + itif]

        process_list = []
        for isub_tif in sub_tif_list:

            flag = os.path.splitext(os.path.basename(isub_tif))[0].split('-')[-1]
            # 判断标签是否存在
            try:
                flag_id = flag_dict[flag]
            except:
                print('no %s flag' % flag)
                # flag_id = flag_dict['error']
                continue
            # 是否进行筛选
            # if filter_ids != 'none':
            #     filter_id_list = [int(i) for i in filter_ids.split(',')]
            #     if not (flag_id in filter_id_list):
            #         continue

            iout_file = os.path.join(temp_dir,
                                    '%s.csv' % (os.path.splitext(os.path.basename(isub_tif))[0]))

            if os.path.exists(iout_file):
                os.remove(iout_file)

            # out_csv = open(out_file, 'w', newline='')
            # out_csv_writer = csv.writer(out_csv)
            p = Process(target=get_sample_data, args=(in_file, isub_tif, flag_id, int(size_wind), iout_file, ))
            p.start()
            process_list.append(p)

            # get_sample_data(in_file, isub_tif, flag_id, int(size_wind), iout_file,)

            # out_csv.close()
            # out_csv_writer = None

        for ip in process_list:
            ip.join()
        progress(itif / len(tif_list))

    if os.path.exists(out_file):
        os.remove(out_file)

    sys_str = platform.system()
    if (sys_str == 'Windows'):

        cmd_str = r'copy /b *.csv %s' % (out_file)
        # 不打印列表
        subprocess.call(cmd_str, shell=True, stdout=open(os.devnull, 'w'), cwd=temp_dir)

    elif (sys_str == 'Linux'):
        cmd_str = r'cat *.csv > %s' % (out_file)
        # 不打印列表
        subprocess.call(cmd_str, shell=True, stdout=open(os.devnull, 'w'), cwd=temp_dir)
    else:
        print('no system platform')

    # shutil.rmtree(temp_dir)
    progress(1)




if __name__ == '__main__':

    start_time = time.time()

    # if len(sys.argv[1:]) < 5:
    #     sys.exit('Problem reading input')
    # #
    # main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    in_file = r"D:\Data\Test_data\classification\20180804\GF2_20180327_S2_0309_0324_0408_0418tif_sub.tif"
    sample_dir = r"D:\Data\Test_data\classification\20180804\sample_tif_sub"
    size_wind = 7
    flag_file = r"D:\Data\Test_data\classification\20180804\flag.csv"
    out_file = r"D:\Data\Test_data\classification\20180804\gdz_all_csv.csv"
    main(in_file, sample_dir, flag_file, size_wind, out_file)

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))