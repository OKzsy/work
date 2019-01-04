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
import numpy as np
from multiprocessing import Process
from multiprocessing import cpu_count
from keras.models import load_model
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


def run_model(in_file, model_file, size_wind, out_file):

    model = load_model(model_file)

    # 读取csv

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
    num_band = int(len(csv_data[0]) / (size_wind ** 2))

    csv_array = np.array(csv_data).reshape(len(csv_data), size_wind, size_wind, int(num_band))

    # print()
    # temp_data, ind_array = run_jit(in_data, np.array([num_xsize, ysize, num_band, size_wind]))
    # y_pred = model.predict_classes(csv_array / 10000.0, verbose=1)
    y_pred = model.predict_classes(csv_array / 10000.0)


    out_csv = open(out_file, 'w', newline='')
    out_csv_writer = csv.writer(out_csv)

    for iout in range(len(xind_list)):
        out_csv_writer.writerow([xind_list[iout], yind_list[iout], y_pred[iout]])


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

    sys_str = platform.system()
    if (sys_str == 'Windows'):
        # 建立多个进程
        num_proc = int(cpu_count() / 3 * 2)
        for icsv in range(0, len(csv_list), num_proc):

            sub_csv_list = csv_list[icsv: num_proc + icsv]

            process_list = []
            for isub_csv in sub_csv_list:

                iout_file = os.path.join(out_dir,
                                         '%s_class.csv' % (os.path.splitext(os.path.basename(isub_csv))[0]))

                if os.path.exists(iout_file):
                    os.remove(iout_file)

                # out_csv = open(out_file, 'w', newline='')
                # out_csv_writer = csv.writer(out_csv)
                p = Process(target=run_model, args=(isub_csv, model_file, size_wind, iout_file))
                p.start()
                process_list.append(p)

                # out_csv.close()
                # out_csv_writer = None

            for ip in process_list:
                ip.join()
            progress(icsv / len(csv_list))


    elif (sys_str == 'Linux'):

        for icsv in range(len(csv_list)):
            # print(csv_list[icsv])
            iout_file = os.path.join(out_dir,
                                     '%s_class.csv' % (os.path.splitext(os.path.basename(csv_list[icsv]))[0]))
            run_model(csv_list[icsv], model_file, size_wind, iout_file)
            progress(icsv / len(csv_list))

    else:
        print('no system platform')

    progress(1)



if __name__ == '__main__':
    start_time = time.time()

    if len(sys.argv[1:]) < 1:
        sys.exit('Problem reading input')

    all_argv = str(sys.argv[1])
    list_argv = all_argv.split(',')
    main(list_argv[0], list_argv[1], int(list_argv[2]), list_argv[3])

    # in_dir = r"D:\Data\Test_data\un_zip\out_dir\test5"
    # model_file  =  r"C:\Users\01\Desktop\yingqiao\model\lr\lr_0.00008\model-ep050-loss0.287-val_loss0.276-acc0.881-val_cc0.886.h5"
    # out_dir = r"D:\Data\Test_data\un_zip\out_dir\test5_class"
    # size_wind = 7

    # in_dir = r'D:\Data\Test_data\分类\test_block_1'
    # model_file = r"D:\Data\Test_data\分类\cnn1_patch_model.h5"
    # out_dir = r'D:\Data\Test_data\分类\out_class'
    # size_wind = 7
    # main(in_dir, model_file, size_wind, out_dir)

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))