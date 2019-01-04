#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/8/22 09:40

Description:
    利用python多进程生成深度学习，训练样本

Parameters
    参数1：样本所在文件夹,样本命名方式必须是xxxx-yaocao.tif
    参数2：窗口大小
    参数3：标签文件路径(.csv),如果输入1，并需要修改代码
    参数4：输出csv文件路径

"""

import os
import sys
import time
import csv
import random
import string
import tempfile
import shutil
import subprocess
import platform
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

# # 文件直角(笛卡尔)坐标转成文件地理坐标
# def pixel2map(pixelx, pixely, in_geo):
#     mapx = in_geo[0] + pixelx * in_geo[1]
#     mapy = in_geo[3] + pixely * in_geo[5]
#     return mapx, mapy
#
# # 地理文件坐标转成文件直角(笛卡尔)坐标
# def map2pixel(mapx, mapy, in_geo):
#     pixelx = (mapx - in_geo[0]) / in_geo[1] + 0.5
#     pixely = (mapy - in_geo[3]) / in_geo[5] + 0.5
#     return int(pixelx), int(pixely)



# 实现选出文件夹内每一类作物的包含0的图像块的数据
# def cut(data1, data2, n):
#     M, N, c = data1.shape
#     # print(data1.shape)
#     r = int(n / 2)
#     a = []
#     for i in range(r, M - r):
#         for j in range(r, N - r):
#             if data1[i, j, :].ravel()[0] > 0:
#             # if 0 not in data1[i, j]:
#                 patch2 = data2[(i - r):(i + r + 1), (j - r):(j + r + 1), :]
#                 a.append(patch2.ravel())
#             else:
#                 continue
#
#     return np.array(a)

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

def search_flag_file(folder_path, file_extension):
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
            file_flag = os.path.splitext(os.path.basename(ifile))[0].split('-')[-1]
            if file_flag == iflag:
                iflag_list.append(ifile)
        out_dict[iflag] = iflag_list
    return out_dict, search_files

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

def run_img2csv(in_list):

    flag_sample_tifs = in_list[0]
    flag_dict = in_list[1]
    csv_dir = in_list[2]
    patch_size = in_list[3]

    for itif in range(len(flag_sample_tifs)):

        base_name = os.path.splitext(os.path.basename(flag_sample_tifs[itif]))[0]

        try:
            iflag_id = flag_dict[base_name.split('-')[-1]]
        except:
            iflag_id = flag_dict['other']

        # base_name = os.path.splitext(os.path.basename(flag_sample_tifs))[0]

        # 读取影像数据
        sample_sds = gdal.Open(flag_sample_tifs[itif])
        if sample_sds is None:
            continue
            #sys.exit('%s problem' % flag_sample_tifs[itif])

        xsize = sample_sds.RasterXSize
        ysize = sample_sds.RasterYSize

        if (xsize < patch_size) or (ysize < patch_size):
            sample_sds = None
            continue
        # print(flag_sample_tifs[itif])
        sample_data = sample_sds.ReadAsArray(0, 0, xsize, ysize).transpose(1, 2, 0)
        # 切块，段
        out_data = cut_array(sample_data , patch_size)

        if len(out_data) == 0:
            continue

        iout_file = os.path.join(csv_dir, '%s.csv' % (base_name))

        if os.path.exists(iout_file):
            os.remove(iout_file)

        out_csv = open(iout_file, 'w', newline='')
        out_csv_writer = csv.writer(out_csv)
        for ipixel in range(out_data.shape[0]):
            out_csv_writer.writerow(np.array(out_data)[ipixel, :].tolist() + [iflag_id])


        out_data = None
        sample_sds = None
        sample_img_sds = None
        sample_data = None
        sample_img_data = None
        out_csv.close()
        out_csv_writer = None



def main(sample_dir, patch_size, flag_file, out_file):

    # 新建缓存文件夹
    sys_str = platform.system()
    if (sys_str == 'Windows'):
        temp_dir = os.path.join(tempfile.gettempdir(), 'gdal_temp2')
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.mkdir(temp_dir)
    else:
        rand_str = ''.join(random.sample(string.ascii_letters + string.digits, 4))
        temp_dir = os.path.join(tempfile.gettempdir(), 'gdal_%s' % rand_str)
        if not os.path.exists(temp_dir):
            os.mkdir(temp_dir)

    sample_dict, sample_tifs = search_flag_file(sample_dir, '.tif')

    csv_dir = os.path.join(temp_dir, 'sample_flag_csv')
    if os.path.exists(csv_dir):
        shutil.rmtree(csv_dir)
    os.mkdir(csv_dir)

    # 需要修改

    if flag_file == '1':

        flag_dict = {'dasuan': 0, 'xiaomai': 1, 'other': 2}
    else:
        flag_dict = get_flag(flag_file)
    # get_flag()
    # run_get_csv_sample([sample_tifs, img_sample_tifs, flag_dict, csv_dir, patch_size])

    sys_str = platform.system()
    if (sys_str == 'Windows'):
        num_proc = int(mp.cpu_count() )
    else:
        num_proc = int(mp.cpu_count() - 1)

    if len(sample_tifs) < num_proc:
        num_proc = len(sample_tifs)
        block_num_file = 1
    else:
        block_num_file = int(len(sample_tifs) / num_proc)

    pool = mp.Pool(processes=num_proc)

    for iproc in range(num_proc):

        if iproc == (num_proc - 1):
            sub_in_files = sample_tifs[(iproc * block_num_file):]
        else:
            sub_in_files = sample_tifs[(iproc * block_num_file): (iproc * block_num_file) + block_num_file]

        in_list = [sub_in_files, flag_dict, csv_dir, patch_size]

        pool.apply_async(run_img2csv, args=(in_list,))

    pool.close()
    pool.join()


    if os.path.exists(out_file):
        os.remove(out_file)

    sys_str = platform.system()
    if (sys_str == 'Windows'):

        cmd_str = r'copy /b *.csv %s' % (out_file)
        # 不打印列表
        subprocess.call(cmd_str, shell=True, stdout=open(os.devnull, 'w'), cwd=csv_dir)

    elif (sys_str == 'Linux'):
        cmd_str = r'cat *.csv > %s' % (out_file)
        # 不打印列表
        subprocess.call(cmd_str, shell=True, stdout=open(os.devnull, 'w'), cwd=csv_dir)
    else:
        print('no system platform')

    shutil.rmtree(temp_dir)


if __name__ == '__main__':
    start_time = time.time()

    # sample_dir = r'D:\Data\Test_data\classification\20180815\new_sample_tif'
    # patch_size = 7
    # flag_file =''
    # out_file = r'D:\Data\Test_data\classification\20180815\all_samples_3.csv'
    # main(sample_dir, patch_size, flag_file, out_file)

    if len(sys.argv[1:]) < 4:
        sys.exit('Problem reading input')

    main(sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4])

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))