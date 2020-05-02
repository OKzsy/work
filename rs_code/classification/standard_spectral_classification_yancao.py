#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/8/29 9:18

Description:
    利用光谱角、光谱距离，计算地物标准光谱，并利用标准光谱，生成光谱概率影像

Parameters
    参数1: 输入待计算光谱概率的基准影像
    参数2: 输入样本tif所在目录(tif名称必须是xx-xiaomai.tif)
    参数3: 输入筛选光谱的条件(四分位法的 boxs cale)， ++++ 可选，默认为1.5 ++++
    参数4: 输出标准光谱的csv路径
    参数5: 输出概率影像的路径(.tif)

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
import subprocess
import multiprocessing as mp

import numpy as np
import numba as nb
import pandas as pd
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

@nb.jit
def calc_prob(w, o):
    cos = np.dot(w, o) / (np.linalg.norm(w) * np.linalg.norm(o))  # 向量夹角
    n = w.shape[0]
    dist = 1 - (np.linalg.norm(w - o) / np.sqrt(n))  # 距离
    p = cos * dist
    return p


@nb.jit
def get_prob(in_data, standard_array):

    # 读取csv
    ysize = in_data.shape[1]
    xsize = in_data.shape[2]

    num_flag = standard_array.shape[0]
    flag_p = np.empty((ysize, xsize, num_flag), dtype=np.int16)
    flag_p[:, :, :] = 0


    for iyoffset in range(ysize):
        for ixoffset in range(xsize):

            if in_data[0, iyoffset, ixoffset] <= 0:
                continue

            isample_data = in_data[:, iyoffset, ixoffset] * 1.0

            for iflag in range(num_flag):

                iprob = calc_prob(isample_data / 10000, standard_array[iflag, :] / 10000) * 10000
                if (iprob > 0) and (iprob <= 10000) :
                    flag_p[iyoffset, ixoffset, iflag] = iprob
                iprob = None

            isample_data = None

    return flag_p

def run_get_prob(in_list):

    in_files = in_list[0:-2]
    standard_spec_array = in_list[-2]
    out_dir = in_list[-1]

    for in_file in in_files:


        sds = gdal.Open(in_file)

        if sds is None:
            continue

        xsize = sds.RasterXSize
        ysize = sds.RasterYSize

        idata = sds.ReadAsArray(0, 0, xsize, ysize).astype(np.float32) / 10000
        # ndvi, gdnvi, evi
        idata[np.where(idata == 0)] = np.nan

        # print(len(idata[0, :, :][np.where((idata[3, :, :] + idata[2, :, :]) == 0)]), len(idata[0, :, :][np.where((idata[3, :, :] + idata[1, :, :]) == 0)]),
        #       len(idata[0, :, :][np.where((idata[3, :, :] + 6.0 * idata[2, :, :] - 7.5 * idata[0, :, :] + 1) == 0)]))
        # 除去0
        # ndvi_den = idata[3, :, :] + idata[2, :, :]
        # ndvi_den[np.where(ndvi_den == 0)] = np.nan

        gndvi_den = idata[3, :, :] + idata[1, :, :]
        gndvi_den[np.where(gndvi_den == 0)] = np.nan

        # evi_den = idata[3, :, :] + 6.0 * idata[2, :, :] - 7.5 * idata[0, :, :] + 1
        # evi_den[np.where(evi_den == 0)] = np.nan

        # ndvi = (idata[3, :, :] - idata[2, :, :]) / ndvi_den
        gndvi = (idata[3, :, :] - idata[1, :, :]) / gndvi_den
        # evi = 2.5 * (idata[3, :, :] - idata[2, :, :]) / evi_den
        # idata = np.append(idata, ndvi.reshape(1, ysize, xsize), 0)
        idata = np.append(idata, gndvi.reshape(1, ysize, xsize), 0)
        # idata = np.append(idata, evi.reshape(1, ysize, xsize), 0)

        idata[np.isnan(idata)] = 0

        idata = (idata * 10000).astype(np.int)

        flag_p = get_prob(idata, standard_spec_array)

        idata = None
        ndvi = None
        gndvi =None
        evi = None
        ndvi_den = None
        gndvi_den = None
        evi_den = None

        out_file = os.path.join(out_dir, '%s_prob.tif' %
                                (os.path.splitext(os.path.basename(in_file))[0]))

        out_driver = gdal.GetDriverByName('GTiff')
        #
        if os.path.exists(out_file):
            out_driver.Delete(out_file)
        out_dataset = out_driver.Create(out_file, xsize, ysize, flag_p.shape[2], gdal.GDT_Int16)

        for iband in range(flag_p.shape[2]):
            out_band = out_dataset.GetRasterBand(1 + iband)

            out_band.WriteArray(flag_p[:, :, iband].reshape(ysize, xsize), 0, 0)
            out_band = None

        flag_p = None
        sds = None
        out_dataset = None
        out_band = None

def read_csv(in_file):

    # s = pd.read_csv(in_file, header=None, nrows=1, engine = 'python')
    csv_shape = pd.read_csv(in_file, header=None, nrows=1, engine = 'python').shape

    out_data = np.zeros((csv_shape[0], csv_shape[1]), dtype=np.float)

    chunksize = 10 ** 6
    for chunk in pd.read_csv(in_file, header=None, chunksize=chunksize, engine = 'python'):
        out_data = np.vstack((out_data, chunk.values))
        chunk = None

    return out_data[1:, :]


@nb.jit
def calc_mean(flag, in_file, box_scale):
    csv_data = read_csv(in_file)
    ind_data = np.zeros((csv_data.shape[0], csv_data.shape[1]), dtype=np.byte)

    band_range = []
    # box_scale = 1.5
    for iband in range(csv_data.shape[1]):
        band_data = csv_data[:, iband]

        band_low = np.percentile(band_data, 25)
        band_upper = np.percentile(band_data, 75)
        band_inter = (band_low - box_scale * (band_upper - band_low),
                      box_scale * (band_upper - band_low) + band_upper)

        ind_useful = np.where((band_data >= band_inter[0]) & (band_data <= band_inter[1]))
        ind_data[:, iband][ind_useful] = 1

        band_range.append(band_inter)

    use_ind = []
    imean_array = np.zeros((ind_data.shape[1]), np.float)
    imax_array = csv_data[0, :].astype(np.float)
    imin_array = csv_data[0, :].astype(np.float)

    for isample in range(ind_data.shape[0]):
        isample_ind = ind_data[isample, :]

        if np.all(isample_ind == np.ones((ind_data.shape[1]), dtype=np.byte)):
            use_ind.append(isample)
            isample_data = csv_data[isample, :]

            imax_array = np.maximum(imax_array, csv_data[isample, :])
            imin_array = np.minimum(imin_array, csv_data[isample, :])

            # for iband in range(len(isample_data)):
            #     if imax_array[iband]
            imean_array = imean_array + csv_data[isample, :]

            # print('ok')
        else:
            # print('no')
            continue
    print(flag, csv_data.shape[0], len(use_ind), int(len(use_ind) / csv_data.shape[0] * 100))

    return imean_array / len(use_ind), imax_array, imin_array


@nb.jit
def get_spec(in_data, out_file):
    ysize = in_data.shape[1]
    xsize = in_data.shape[2]

    # 写入csv
    out_csv = open(out_file, 'w', newline='')
    out_csv_writer = csv.writer(out_csv)

    for iyoffset in range(3, ysize-3, 1):
        for ixoffset in range(3, xsize-3, 1):

            if in_data[0, iyoffset, ixoffset] <= 0:
                continue

            isample_data = in_data[:, iyoffset, ixoffset]

            out_csv_writer.writerow(isample_data.flatten().tolist())

            # temp_data = np.vstack((temp_data, isample_data.T.flatten()))
            # xind_list.append(iyoffset)
            # yind_list.append(ixoffset)

            isample_data = None

    out_csv.close()
    out_csv_writer = None


def search_flag(folder_path, file_extension):

    flag = []
    search_files = []
    for dir_path, dir_names, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(file_extension) and (str(os.path.splitext(file)[0].split('-')[-1]) == 'huasheng'):
                flag.append(str(os.path.splitext(file)[0].split('-')[-1]))
                search_files.append(os.path.normpath(os.path.join(dir_path, file)))

    flag_set = list(set(flag))
    flag_set.sort(key=flag.index)
    out_dict = {}
    for iflag in flag_set:

        iflag_list = []
        for ifile in search_files:
            file_flag = str(os.path.splitext(os.path.basename(ifile))[0].split('-')[-1])
            if file_flag == iflag:
                iflag_list.append(ifile)
        out_dict[iflag] = iflag_list
    return out_dict

def block_raster(in_file, block_dir):

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

        resahpe_file = os.path.join(block_dir, '%s_%d_%d_%d_%d.tif' %
                                    (os.path.splitext(os.path.basename(in_file))[0], xoffset, 0, num_xsize, ysize))

        # 设置输出影像
        out_driver = gdal.GetDriverByName('GTiff')

        if os.path.exists(resahpe_file):
            out_driver.Delete(resahpe_file)
        reshape_dataset = out_driver.Create(resahpe_file, num_xsize, ysize, num_band, data_type)

        for iband in range(num_band):
            in_band = source_dataset.GetRasterBand(1 + iband)

            out_band = reshape_dataset.GetRasterBand(1 + iband)

            in_data = in_band.ReadAsArray(xoffset, 0, num_xsize, ysize)

            out_band.WriteArray(in_data, 0, 0)

            in_data = None
            in_band = None
            out_band = None
        reshape_dataset = None

        # progress((xoffset + num_xsize) / xsize)
    source_dataset = None

def read_raster(in_file):
    source_dataset = gdal.Open(in_file)

    if source_dataset is None:
        sys.exit('Problem opening file %s!' % in_file)

    xsize = source_dataset.RasterXSize
    ysize = source_dataset.RasterYSize
    num_band = source_dataset.RasterCount
    geotransform = source_dataset.GetGeoTransform()
    projection = source_dataset.GetProjectionRef()
    data_type = source_dataset.GetRasterBand(1).DataType

    # in_data = source_dataset.ReadAsArray(0, 0, xsize, ysize)
    source_dataset = None

    return [xsize, ysize, geotransform, projection]


def main(in_file, in_dir, box_scale, out_csv_file, out_p_file):

    in_dict = search_flag(in_dir, 'tif')
    flag_list = list(in_dict.keys())


    out_csv_dir = os.path.join(temp_dir, 'out_csv')
    if os.path.exists(out_csv_dir):
        shutil.rmtree(out_csv_dir)
    os.mkdir(out_csv_dir)
    # 写入csv
    out_csv = open(out_csv_file, 'w', newline='')
    out_csv_writer = csv.writer(out_csv)

    #
    standard_spec = []
    for iflag in flag_list:
        flag_files = in_dict[iflag]

        flag_dir = os.path.join(out_csv_dir, '%s' % iflag)
        if os.path.exists(flag_dir):
            shutil.rmtree(flag_dir)

        os.mkdir(flag_dir)

        for iflag_file in flag_files:
            iout_file = os.path.join(flag_dir, '%s.csv'
                                     % (os.path.splitext(os.path.basename(iflag_file)))[0])

            source_dataset = gdal.Open(iflag_file)

            if source_dataset is None:
                sys.exit('Problem opening file %s!' % iflag_file)

            xsize = source_dataset.RasterXSize
            ysize = source_dataset.RasterYSize

            idata = source_dataset.ReadAsArray(0, 0, xsize, ysize).astype(np.float32) / 10000
            # ndvi, gdnvi, evi
            idata[np.where(idata == 0)] = np.nan

            # 除去0
            # ndvi_den = idata[3, :, :] + idata[2, :, :]
            # ndvi_den[np.where(ndvi_den == 0)] = np.nan

            gndvi_den = idata[3, :, :] + idata[1, :, :]
            gndvi_den[np.where(gndvi_den == 0)] = np.nan

            # evi_den = idata[3, :, :] + 6.0 * idata[2, :, :] - 7.5 * idata[0, :, :] + 1
            # evi_den[np.where(evi_den == 0)] = np.nan

            # ndvi = (idata[3, :, :] - idata[2, :, :]) / ndvi_den
            gndvi = (idata[3, :, :] - idata[1, :, :]) / gndvi_den
            # evi = 2.5 * (idata[3, :, :] - idata[2, :, :]) / evi_den
            # idata = np.append(idata, ndvi.reshape(1, ysize, xsize), 0)
            idata = np.append(idata, gndvi.reshape(1, ysize, xsize), 0)
            # idata = np.append(idata, evi.reshape(1, ysize, xsize), 0)

            idata[np.isnan(idata)] = 0

            idata = (idata * 10000).astype(np.int)

            get_spec(idata, iout_file)

            idata = None
            ndvi = None
            gndvi = None
            evi = None
            evi_den = None
            ndvi_den = None
            gndvi_den = None

            source_dataset = None

        out_file = os.path.join(out_csv_dir, '%s.csv' % iflag)
        if (sys_str == 'Windows'):

            cmd_str = r'copy /b *.csv %s' % (out_file)
            # 不打印列表
            # subprocess.call(cmd_str, shell=True, stdout=open(os.devnull, 'w'), cwd=flag_dir)

        elif (sys_str == 'Linux'):
            cmd_str = r'cat *.csv > %s' % (out_file)

        else:
            sys.exit('no system platform')

        # 不打印列表
        subprocess.call(cmd_str, shell=True, stdout=open(os.devnull, 'w'), cwd=flag_dir)
        mean_array, max_array, min_array = calc_mean(iflag, out_file, box_scale)

        #gdnvi
        # gndvi = (mean_array[3] - mean_array[1]) / (mean_array[3] + mean_array[1]) * 10000
        # mean_array = np.append(mean_array, gndvi)

        out_csv_writer.writerow(['%s_mean' % iflag] + mean_array.flatten().tolist())
        standard_spec.append(mean_array.flatten())
        # out_csv_writer.writerow(['%s_max' % iflag] + max_array.flatten().tolist())
        # out_csv_writer.writerow(['%s_min' % iflag] + min_array.flatten().tolist())
    out_csv.close()
    out_csv_writer = None

    standard_spec_array =  np.array(standard_spec)

    progress(0.1)

    # 切块
    block_dir = os.path.join(temp_dir, 'block_tif')
    if os.path.exists(block_dir):
        shutil.rmtree(block_dir)
    os.mkdir(block_dir)
    block_raster(in_file, block_dir)
    progress(0.25)
    # 计算概率
    tif_files = search_file(block_dir, '.tif')

    if tif_files == []:
        sys.exit('no tif')

    out_prob_dir = os.path.join(temp_dir, 'prob_tif')
    if os.path.exists(out_prob_dir):
        shutil.rmtree(out_prob_dir)
    os.mkdir(out_prob_dir)

    # run_get_prob(tif_files + [standard_spec_array, out_prob_dir])

    # 建立进程池
    if (sys_str == 'Windows'):
        num_proc = int(mp.cpu_count() * 1 / 2)
    else:
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

        in_list = sub_in_files + [standard_spec_array, out_prob_dir]

        pool.apply_async(run_get_prob, args=(in_list,))

        progress(0.25 + iproc / num_proc * 0.65)

    pool.close()
    pool.join()


    prob_files = search_file(out_prob_dir, '.tif')
    file_info_list = read_raster(in_file)

    out_driver = gdal.GetDriverByName('GTiff')
    # # #
    if os.path.exists(out_p_file):
        out_driver.Delete(out_p_file)
    out_dataset = out_driver.Create(out_p_file, file_info_list[0], file_info_list[1], standard_spec_array.shape[0], gdal.GDT_Int16)

    for itif_file in prob_files:
        file_range = os.path.splitext(os.path.basename(itif_file))[0].split('_')[-5:-1]

        sds = gdal.Open((itif_file))

        for iband in range(standard_spec_array.shape[0]):
            out_band = out_dataset.GetRasterBand(1 + iband)

            in_data = sds.GetRasterBand(1 + iband).ReadAsArray(0, 0, int(file_range[2]), int(file_range[3]))

            out_band.WriteArray(in_data, int(file_range[0]), int(file_range[1]))

            in_data = None
            out_band = None
        sds = None

    out_dataset.SetGeoTransform(file_info_list[2])
    out_dataset.SetProjection(file_info_list[3])

    source_dataset = None
    out_dataset = None

    shutil.rmtree(temp_dir)

    progress(1)


if __name__ == '__main__':
    start_time = time.time()

    # if len(sys.argv[1:]) < 4:
    #     sys.exit('Problem reading input')
    # if len(sys.argv[1:]) == 5:
    #     in_file = sys.argv[1]
    #     in_dir = sys.argv[2]
    #     box_scale = float(sys.argv[3])
    #     out_csv_file = sys.argv[4]
    #     out_p_file = sys.argv[5]
    # else:
    #     in_file = sys.argv[1]
    #     in_dir = sys.argv[2]
    #     out_csv_file = sys.argv[3]
    #     out_p_file = sys.argv[4]
    #     box_scale = 1.5
    #
    # # 新建缓存文件夹
    sys_str = platform.system()
    # if (sys_str == 'Windows'):
    #     temp_dir = os.path.join(tempfile.gettempdir(), 'gdal_temp')
    #     if os.path.exists(temp_dir):
    #         shutil.rmtree(temp_dir)
    #     os.mkdir(temp_dir)
    # else:
    #     rand_str = ''.join(random.sample(string.ascii_letters + string.digits, 4))
    #     temp_dir = os.path.join(tempfile.gettempdir(), 'gdal_%s' % rand_str)
    #     if not os.path.exists(temp_dir):
    #         os.mkdir(temp_dir)

    # main(in_file, in_dir, box_scale, out_csv_file, out_p_file)

    # try:
    #     main(in_file, in_dir, box_scale, out_csv_file, out_p_file)
    # except:
    #     shutil.rmtree(temp_dir)

    temp_dir = os.path.join(tempfile.gettempdir(), 'gdal_temp')
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.mkdir(temp_dir)
    in_file = r"\\192.168.0.234\nydsj\user\ZSS\农保项目\S2\62xianque_out\res\L2A_T50SKC_A021665_20190816T031414_ref_10m-prj.tif"
    in_dir = r'F:\test_data\tmp_out'
    box_scale = 1
    out_csv_file = r'F:\test_data\tmp_out\standad_spec7.csv'
    out_p_file = r"F:\test_data\tmp_out\roi1_prob7.tif"
    main(in_file, in_dir, box_scale, out_csv_file, out_p_file)

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))