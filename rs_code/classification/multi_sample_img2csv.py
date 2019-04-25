#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/12/21 17:06

Description:
    利用python多进程生成深度学习，训练样本

Parameters
    参数1：样本所在文件夹,样本命名方式必须是xxxx-yaocao.tif
    参数2：窗口大小
    参数3：标签文件路径(.csv),如果输入1，并需要修改代码

"""

import os
import sys
import time
import multiprocessing as mp
import numpy as np
import numba as nb

try:
    from osgeo import gdal, ogr
except ImportError:
    import gdal, ogr

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress

@nb.jit
def cut_array(sample_data, patch_size):

    re_xszie, re_ysize, num_band = sample_data.shape
    # print(data1.shape)
    sub_patch_size = int(patch_size / 2)
    out_data = []
    for i in range(sub_patch_size, re_xszie - sub_patch_size):
        for j in range(sub_patch_size, re_ysize - sub_patch_size):
            if np.min(sample_data[i, j, :]) > 0:
                # if 0 not in data1[i, j]:
                iout_data = sample_data[(i - sub_patch_size):(i + sub_patch_size + 1),
                            (j - sub_patch_size):(j + sub_patch_size + 1), :]
                if np.min(iout_data) > 0:
                    out_data.append(iout_data.ravel())
                iout_data = None
            # else:
            #     continue
    return np.array(out_data)

def search_file(folder_path, file_extension):

    search_files = []
    for dir_path, dir_names, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(file_extension):
                search_files.append(os.path.normpath(os.path.join(dir_path, file)))
    return search_files

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

def img2array(in_list):

    sample_tifs = in_list[0]
    flag_dict = in_list[1]
    patch_size = in_list[2]

    for itif in range(len(sample_tifs)):

        base_name = os.path.splitext(os.path.basename(sample_tifs[itif]))[0]

        try:
            iflag_id = flag_dict[base_name.split('-')[-1]]
        except:
            iflag_id = flag_dict['qita']

        # base_name = os.path.splitext(os.path.basename(sample_tifs))[0]

        # 读取影像数据
        sample_sds = gdal.Open(sample_tifs[itif])
        if sample_sds is None:
            continue
            #sys.exit('%s problem' % sample_tifs[itif])

        xsize = sample_sds.RasterXSize
        ysize = sample_sds.RasterYSize

        if (xsize < patch_size) or (ysize < patch_size):
            sample_sds = None
            continue
        # print(sample_tifs[itif])
        sample_data = sample_sds.ReadAsArray(0, 0, xsize, ysize).transpose(1, 2, 0)
        # 切块，段
        out_data = cut_array(sample_data , patch_size)

        if len(out_data.flatten()) == 0:
            continue

        flag_data = np.zeros((out_data.shape[0], 1), dtype=np.byte)
        flag_data[:, :] = iflag_id

        out_data = np.column_stack((out_data, flag_data))

        return out_data

def sample_img2array(sample_dir, patch_size, flag_file):

    sample_files = search_file(sample_dir, '.tif')
    flag_dict = get_flag(flag_file)

    num_band = gdal.Open(sample_files[0]).RasterCount

    # run_img2csv([sample_files, flag_dict, csv_dir, patch_size])

    num_proc = int(mp.cpu_count() - 1)
    if len(sample_files) < num_proc:
        num_proc = len(sample_files)
        block_num_file = 1
    else:
        block_num_file = int(len(sample_files) / num_proc)

    out_data = np.zeros((1, patch_size*patch_size*num_band+1), dtype=np.int16)

    r_list = [] # 进程返回结果
    pool = mp.Pool(processes=num_proc)

    for iproc in range(num_proc):

        if iproc == (num_proc - 1):
            sub_in_files = sample_files[(iproc * block_num_file):]
        else:
            sub_in_files = sample_files[(iproc * block_num_file): (iproc * block_num_file) + block_num_file]

        in_list = [sub_in_files, flag_dict, patch_size]

        r_list.append(pool.apply_async(img2array, args=(in_list,)))

    pool.close()
    pool.join()

    for r in r_list:
        r_get_data = r.get()
        out_data = np.row_stack((out_data, r_get_data))# 获取进程结果

    out_data = out_data[1:, :]

    # print(out_data[0,:])

    return out_data

if __name__ == '__main__':
    start_time = time.time()

    # sample_dir = r'\\192.168.0.234\nydsj\user\TJG\classification\20181221\out_tif'
    # patch_size = 7
    # flag_file = r"\\192.168.0.234\nydsj\user\TJG\classification\20181221\flag.csv"
    # sample_img2array(sample_dir, patch_size, flag_file)

    if len(sys.argv[1:]) < 3:
        sys.exit('Problem reading input')

    sample_img2array(sys.argv[1], int(sys.argv[2]), sys.argv[3])

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))