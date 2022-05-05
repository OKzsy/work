#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2020/4/30 15:58
# @Author  : zhaoss
# @FileName: sample.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
将裁剪出来的样本影像块按照标签文件生成样本数据，可以选择是否自动均衡不平衡样本

Parameters


"""

import os
import sys
import platform
import glob
import time
import fnmatch
import subprocess
import tempfile
import shutil
import numba as nb
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def searchfiles(dirpath, partfileinfo='*', recursive=False):
    """列出符合条件的文件（包含路径），默认不进行递归查询，当recursive为True时同时查询子文件夹
        并返回品类列表
    """
    # 定义结果输出列表
    filelist = []
    catelist = []
    # 列出根目录下包含文件夹在内的所有文件目录
    pathlist = glob.glob(os.path.join(os.path.sep, dirpath, "*"))
    # 逐文件进行判断
    for mpath in pathlist:
        if os.path.isdir(mpath):
            # 默认不判断子文件夹
            if recursive:
                filelist += searchfiles(mpath, partfileinfo, recursive)
        elif fnmatch.fnmatch(os.path.basename(mpath), partfileinfo):
            filelist.append(mpath)
            basename = os.path.splitext(os.path.basename(mpath))[0]
            cate = basename.split('-')[-1]
            if cate not in catelist:
                catelist.append(cate)

    return filelist, catelist


def img2csv(sample, tmp_csv_path, flag):
    """
    将影像中符合要求的像元转换成符合要求的格式进行训练
    :param sample: 样本影像路径
    :param flag: 样本标签
    :return:
    """
    basename = os.path.splitext(os.path.basename(sample))[0]
    iflag_name = basename.split('-')
    iflag = flag[iflag_name[-1]]
    # 拼接该样本的csv的文件
    sample_csv = os.path.join(tmp_csv_path, basename) + '.csv'
    # 打开影像处理样本，当所有像元点不为0时按照要求输出
    sample_ds = gdal.Open(sample)
    sample_arr = sample_ds.ReadAsArray()
    xsize = sample_ds.RasterXSize
    ysize = sample_ds.RasterYSize
    dtype = sample_arr.dtype
    sample_list = []
    for irow in range(ysize):
        for icol in range(xsize):
            point = list(sample_arr[:, irow, icol])
            if np.sum(point) == 0:
                continue
            point.append(iflag)
            sample_list.append(point)
    # 将结果转为np矩阵存储为csv
    sample_list = np.array(sample_list).astype(dtype=dtype)
    # 存储为csv
    if 'int' in str(dtype):
        np.savetxt(sample_csv, sample_list, fmt='%d', delimiter=',')
    else:
        np.savetxt(sample_csv, sample_list, fmt='%.3f', delimiter=',')
    sample_ds = None
    return None


@nb.njit()
def cyunique(a):
    n = a.shape[0]
    label_num = 0
    max_i = a[0]
    min_i = a[0]
    for i in range(n):
        max_i = max(max_i, a[i])
        min_i = min(min_i, a[i])
    min_i = min(min_i, 0)
    max_i -= min_i
    real_total = max_i + 1
    unique = np.zeros(real_total, dtype=np.int16)
    label = np.zeros(real_total, dtype=np.int16)
    label_count = np.zeros(real_total, dtype=np.uint32)
    for i in range(n):
        tmp = a[i] - min_i
        label_count[tmp] += 1
        if not unique[tmp]:
            label_num += 1
            unique[tmp] = 1
            label[tmp] = tmp
    res_label = np.zeros(label_num, dtype=np.int16)
    res_label_count = np.zeros(label_num, dtype=np.uint32)
    ires = 0
    for i in range(real_total):
        if unique[i]:
            res_label[ires] = label[i] + min_i
            res_label_count[ires] = label_count[i]
            ires += 1
    return (res_label, res_label_count)


def equilibrium(tmp_csv, out_csv):
    data = np.loadtxt(tmp_csv, delimiter=',', dtype=np.int16)
    shape = data.shape
    label_static = cyunique(data[:, -1])
    count_label = label_static[0].size
    most_label = max(label_static[1])
    balanced_label_xsize = count_label * most_label
    balanced_label = np.zeros((balanced_label_xsize, shape[1]), dtype=np.int16)
    for ilabel in range(count_label):
        label = label_static[0][ilabel]
        label_count = label_static[1][ilabel]
        x_point = ilabel * most_label
        index = np.where(data[:, -1] == label)
        ori_label_mat = data[index[0], :]
        ori_label_mat_rows = ori_label_mat.shape[0]
        if label_count == most_label:
            balanced_label[x_point: x_point + most_label, :] = ori_label_mat
        else:
            balanced_index = np.random.choice(ori_label_mat_rows, size=most_label, replace=True)
            balanced_label[x_point: x_point + most_label, :] = ori_label_mat[balanced_index, :]
    np.savetxt(out_csv, balanced_label, fmt='%d', delimiter=',')


def main(flag_file, sample_file, out_csv, balance=True):
    # 获取标签
    flag = np.genfromtxt(flag_file, delimiter=',', dtype=None, encoding='utf8')
    flag_dict = dict(flag)
    # 处理每一个样本
    sample_list, category = searchfiles(sample_file, partfileinfo='*.tif')
    tmp_csv_path = tempfile.mkdtemp(dir=os.path.dirname(out_csv))
    count = 0
    total = len(sample_list)
    for isample in sample_list:
        img2csv(isample, tmp_csv_path, flag_dict)
        count += 1
        progress(count / total)
    # 将所有样本csv合并为一个
    out_csv_dir = os.path.dirname(out_csv)
    tmp_csv = os.path.join(out_csv_dir, 'temporary.csv')
    sys_str = platform.system()
    if sys_str == 'Windows':
        cmd_str = r'copy /b *.csv %s' % tmp_csv
        # 不打印列表
        subprocess.call(cmd_str, shell=True, stdout=open(os.devnull, 'w'), cwd=tmp_csv_path)

    elif sys_str == 'Linux':
        cmd_str = r'cat *.csv > %s' % tmp_csv
        # 不打印列表
        subprocess.call(cmd_str, shell=True, stdout=open(os.devnull, 'w'), cwd=tmp_csv_path)
    # 对不均衡的样本均衡化，采用随机复制的方法进行
    if balance:
        equilibrium(tmp_csv, out_csv)
        os.remove(tmp_csv)
    else:
        # 重命名临时文件
        os.rename(tmp_csv, out_csv)
    # 删除临时文件
    shutil.rmtree(tmp_csv_path, ignore_errors=True)


    return None


if __name__ == '__main__':
    # 支持中文路径
    gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
    # 支持中文属性字段
    gdal.SetConfigOption("SHAPE_ENCODING", "GBK")
    # 注册所有ogr驱动
    ogr.RegisterAll()
    # 注册所有gdal驱动
    gdal.AllRegister()
    start_time = time.time()
    balance = True
    flag_file = r"/mnt/e/dengfeng/flag.csv"
    sample_file = r"/mnt/e/dengfeng/out"
    out_csv = r"/mnt/e/dengfeng/sample.csv"
    main(flag_file, sample_file, out_csv, balance)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
