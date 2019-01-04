#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/8/16 16:43

Description:


Parameters


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
import numexpr as ne
import pandas as pd
import numba as nb

try:
    from osgeo import gdal, ogr
except ImportError:
    import gdal, ogr

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



# 实现选出文件夹内每一类作物的包含0的图像块的数据
def cut(data1, data2, n):
    M, N, c = data1.shape
    # print(data1.shape)
    r = int(n / 2)
    a = []
    for i in range(r, M - r):
        for j in range(r, N - r):
            if data1[i, j, :].ravel()[0] > 0:
            # if 0 not in data1[i, j]:
                patch2 = data2[(i - r):(i + r + 1), (j - r):(j + r + 1), :]
                a.append(patch2.ravel())
            else:
                continue

    return np.array(a)

@nb.jit
def cut_array(sample_data, sample_img_data, patch_size):

    re_xszie, re_ysize, num_band = sample_data.shape
    # print(data1.shape)
    sub_patch_size = int(patch_size / 2)
    out_data = []
    for i in range(sub_patch_size, re_xszie - sub_patch_size):
        for j in range(sub_patch_size, re_ysize - sub_patch_size):
            if sample_data[i, j, :].ravel()[0] > 0:
                # if 0 not in data1[i, j]:
                iout_data = sample_img_data[(i - sub_patch_size):(i + sub_patch_size + 1),
                            (j - sub_patch_size):(j + sub_patch_size + 1), :]
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

def run_get_csv_sample(in_list):

    flag_sample_tifs = in_list[0]
    flag_img_sample_tifs = in_list[1]
    flag_dict = in_list[2]
    csv_dir = in_list[3]
    patch_size = in_list[4]

    for itif in range(len(flag_sample_tifs)):

        base_name = os.path.splitext(os.path.basename(flag_sample_tifs[itif]))[0]

        try:
            iflag_id = flag_dict[base_name.split('-')[-1]]
        except:
            iflag_id = 2

        # base_name = os.path.splitext(os.path.basename(flag_sample_tifs))[0]

        # 读取影像数据
        sample_sds = gdal.Open(flag_sample_tifs[itif])
        if sample_sds is None:
            sys.exit('%s problem' % flag_sample_tifs[itif])

        sample_img_sds = gdal.Open(flag_img_sample_tifs[itif])
        if sample_img_sds is None:
            sys.exit('%s problem' % flag_img_sample_tifs[itif])

        xsize = sample_sds.RasterXSize
        ysize = sample_sds.RasterYSize

        if (xsize < patch_size) or (ysize < patch_size):
            sample_sds = None
            sample_img_sds = None
            continue
        print(flag_sample_tifs[itif])
        sample_data = sample_sds.ReadAsArray(0, 0, xsize, ysize).transpose(1, 2, 0)
        sample_img_data = sample_img_sds.ReadAsArray(0, 0, xsize, ysize).transpose(1, 2, 0)

        # 切块，段
        out_data = cut_array(sample_data, sample_img_data, patch_size)

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

def run_get_img_sample(in_list):

    tif_list = in_list[:-2]
    in_file = in_list[-2]
    img_sample_dir = in_list[-1]

    source_dataset = gdal.Open(in_file)
    if source_dataset is None:
        sys.exit('Problem opening file %s!' % in_file)

    # 基准影像空间参考
    geotransform = source_dataset.GetGeoTransform()
    num_band = source_dataset.RasterCount

    out_driver = gdal.GetDriverByName('GTiff')

    for itif in range(len(tif_list)):

        iout_file = os.path.join(img_sample_dir, '%s' % (os.path.basename(tif_list[itif])))

        sds = gdal.Open(tif_list[itif])
        xsize = sds.RasterXSize
        ysize = sds.RasterYSize
        geo = sds.GetGeoTransform()
        proj = sds.GetProjectionRef()
        data_type = sds.GetRasterBand(1).DataType
        x_pos, y_pos = map2pixel(geo[0], geo[3], geotransform)

        if (x_pos < 0) or (y_pos < 0):
            sds = None

            out_driver.Delete(tif_list[itif])
            continue

        if os.path.exists(iout_file):
            out_driver.Delete(iout_file)
        out_dataset = out_driver.Create(iout_file, xsize, ysize, num_band, data_type)
        out_dataset.SetGeoTransform(geo)
        out_dataset.SetProjection(proj)
        for iband in range(num_band):
            out_band = out_dataset.GetRasterBand(1 + iband)
            out_band.WriteArray(source_dataset.GetRasterBand(1 + iband).ReadAsArray(x_pos, y_pos, xsize, ysize), 0, 0)
            out_band = None
        sds = None
        out_dataset = None
    source_dataset = None

def get_img_sample(in_file, input_files, img_sample_dir, num_proc):

    # 切出矩形
    # source_dataset = gdal.Open(in_file)
    # if source_dataset is None:
    #     sys.exit('Problem opening file %s!' % in_file)

    pool = mp.Pool(processes=num_proc)

    block_num_file = int(len(input_files) / num_proc)

    for iproc in range(num_proc):

        if iproc == (num_proc - 1):
            sub_in_files = input_files[(iproc * block_num_file):]
        else:
            sub_in_files = input_files[(iproc * block_num_file): (iproc * block_num_file) + block_num_file]

        in_list = sub_in_files + [in_file, img_sample_dir]

        pool.apply_async(run_get_img_sample, args=(in_list,))

    pool.close()
    pool.join()



def main(in_file, sample_dir, patch_size, flag_file, out_file):

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

    # 基于样本数据范围在原始影像上进行切块
    img_sample_dir = os.path.join(temp_dir, 'img_sample_tif')
    if not os.path.exists(img_sample_dir):
        os.mkdir(img_sample_dir)

    sample_dict, sample_tifs = search_flag_file(sample_dir, '.tif')
    # 可修改
    num_proc = int(mp.cpu_count() * 1 / 2)

    get_img_sample(in_file, sample_tifs, img_sample_dir, num_proc)

    img_sample_dict, img_sample_tifs = search_flag_file(img_sample_dir, '.tif')

    sample_dict, sample_tifs = search_flag_file(sample_dir, '.tif')

    img_sample_tifs = sorted(img_sample_tifs, reverse=False)
    sample_tifs = sorted(sample_tifs, reverse=False)

    csv_dir = os.path.join(temp_dir, 'sample_flag_csv')
    if os.path.exists(csv_dir):
        shutil.rmtree(csv_dir)
    os.mkdir(csv_dir)

    # 需要修改
    flag_dict = {'dasuan': 0, 'xiaomai': 1}
    # get_flag()
    # run_get_csv_sample([sample_tifs, img_sample_tifs, flag_dict, csv_dir, patch_size])

    pool = mp.Pool(processes=num_proc)

    block_num_file = int(len(sample_tifs) / num_proc)

    for iproc in range(num_proc):

        if iproc == (num_proc - 1):
            sub_in_files = sample_tifs[(iproc * block_num_file):]
            sub_in_img_files = img_sample_tifs[(iproc * block_num_file):]
        else:
            sub_in_files = sample_tifs[(iproc * block_num_file): (iproc * block_num_file) + block_num_file]
            sub_in_img_files = img_sample_tifs[(iproc * block_num_file): (iproc * block_num_file) + block_num_file]

        in_list = [sub_in_files, sub_in_img_files, flag_dict, csv_dir, patch_size]

        pool.apply_async(run_get_csv_sample, args=(in_list,))

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



if __name__ == '__main__':
    start_time = time.time()



    sample_dir = r'D:\Data\Test_data\classification\20180815\new_sample_tif'
    patch_size = 7
    flag_file =''
    out_file = r'D:\Data\Test_data\classification\20180815\all_samples_2.csv'
    in_file = r"D:\Data\Test_data\classification\20180815\duan_zhongmu\GF2_clip.tif"
    main(in_file, sample_dir, patch_size, flag_file, out_file)

    # if len(sys.argv[1:]) < 2:
    #     sys.exit('Problem reading input')

    # main()

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))