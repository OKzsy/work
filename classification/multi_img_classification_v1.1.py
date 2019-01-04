#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/7/11 15:00

Description:
    基于深度学习分类模型，对遥感影像分类

Parameters
    in_dir：分块影像所在路径
    model_file: 深度学习分类模型路径
    size_wind：分类窗口大小
    out_dir：输出分类路径

"""

import os
import sys
import csv
import time
import shutil
import platform
import multiprocessing as mp

import numpy as np
from keras.models import load_model

try:
    from osgeo import gdal
except ImportError:
    import gdal

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress

import warnings
warnings.filterwarnings("ignore", message="numpy.dtype size changed")

def search_file(folder_path, file_extension):
    search_files = []
    for dir_path, dir_names, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(file_extension):
                search_files.append(os.path.normpath(os.path.join(dir_path, file)))
    return search_files


def run_model(in_list):

    import tensorflow as tf
    gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction = 0.1)
    config = tf.ConfigProto(gpu_options = gpu_options)
    sess = tf.Session(config=config)

    in_files = in_list[:-3]
    model_file = in_list[-3]
    size_wind = in_list[-2]
    out_dir = in_list[-1]

    model = load_model(model_file)

    # 读取csv

    for in_file in in_files:

        out_file = os.path.join(out_dir,
                     '%s_class.csv' % (os.path.splitext(os.path.basename(in_file))[0]))


        in_csv = open(in_file, 'r')

        in_csv_reader = csv.reader(in_csv)

        # csv_str = in_csv.readlines()
        csv_data = []
        xind_list = []
        yind_list = []


        for icsv_data in in_csv_reader:

            csv_data.append([np.int(i) for i in icsv_data[2:]])
            xind_list.append(np.int(icsv_data[0]))
            yind_list.append(np.int(icsv_data[1]))

        if csv_data == []:
            in_csv.close()
            continue
        num_band = int(len(csv_data[0]) / (size_wind ** 2))
        csv_array = np.array(csv_data).reshape(len(csv_data), size_wind, size_wind, int(num_band))

        # print()
        # temp_data, ind_array = run_jit(in_data, np.array([num_xsize, ysize, num_band, size_wind]))
        # y_pred = model.predict_classes(csv_array / 10000.0, verbose=1)

        y_pred = model.predict_classes(csv_array / 10000.0, batch_size=1024)

        out_csv = open(out_file, 'w', newline='')
        out_csv_writer = csv.writer(out_csv)

        for iout in range(len(xind_list)):
            out_csv_writer.writerow([xind_list[iout], yind_list[iout], y_pred[iout]])

        print(os.path.basename(in_file))
        out_csv.close()
        in_csv.close()
        out_csv_writer = None
        csv_str = None
        csv_data = None
        csv_array = None
        y_pred = None
        xind_list = None
        yind_list = None
    model = None

def main(in_dir, model_file, size_wind, out_dir):

    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.mkdir(out_dir)

    csv_list = search_file(in_dir, '.csv')

    if csv_list == []:
        sys.exit('no files')
    # csv_list_new = sorted(csv_list, reverse = False)
    # run_model(csv_list_new + [model_file, size_wind, out_dir])

    sys_str = platform.system()
    if (sys_str == 'Windows'):
        num_proc = int(mp.cpu_count() * 1 / 2)
    else:
        num_proc = int(mp.cpu_count() * 1 / 8)

    if len(csv_list) < num_proc:
        num_proc = len(csv_list)
        block_num_file = 1
    else:
        block_num_file = int(len(csv_list) / num_proc)

    # num_proc = 6
    pool = mp.Pool(processes=num_proc)
    for iproc in range(num_proc):

        if iproc == (num_proc - 1):
            sub_in_files = csv_list[(iproc * block_num_file):]
        else:
            sub_in_files = csv_list[(iproc * block_num_file): (iproc * block_num_file) + block_num_file]

        in_list = sub_in_files + [model_file, size_wind, out_dir]

        pool.apply_async(run_model, args=(in_list,))

        progress(iproc / num_proc)
    pool.close()
    pool.join()


    progress(1)



if __name__ == '__main__':
    start_time = time.time()

    if len(sys.argv[1:]) < 4:
        sys.exit('Problem reading input')

    main(sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4])


    # in_dir = r"D:\Data\Test_data\classification\20180825\block_csv1"
    # model_file = r"D:\Data\Test_data\classification\20180825\cnn1_patch_model(4).h5"
    # size_wind = 7
    # out_dir = r"D:\Data\Test_data\classification\20180825\block_csv1_class3"
    # main(in_dir, model_file, size_wind, out_dir)

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))