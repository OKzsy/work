#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2020/9/15 8:41
# @Author  : zhaoss
# @FileName: equilibrium.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import sys
import glob
import time
import numba as nb
import fnmatch
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


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


def main(sample_file, out_sample):
    data = np.loadtxt(sample_file, delimiter=',', dtype=np.int16)
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
        # else:
        #     ilabel_balanced = np.zeros((most_label, shape[1]), dtype=np.int16)
        #     ilabel_balanced[0: ori_label_mat_rows, :] = ori_label_mat
        #     balanced_index = np.random.choice(ori_label_mat_rows, size=most_label - ori_label_mat_rows, replace=True)
        #     extra_ilabel_mat = ori_label_mat[balanced_index, :]
        #
        #     random_ilabel_mat = np.random.rand(*extra_ilabel_mat.shape) * 0.1 + 0.95
        #     extra_ilabel_mat[:, 0: -1] = (extra_ilabel_mat[:, 0: -1] * random_ilabel_mat[:, 0: -1]).astype(np.int16)
        #     ilabel_balanced[ori_label_mat_rows:, :] = extra_ilabel_mat
        #     balanced_label[x_point: x_point + most_label, :] = ilabel_balanced
    np.savetxt(out_sample, balanced_label, fmt='%d', delimiter=',')


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
    samplefile = r"\\192.168.0.234\nydsj\user\ZSS\2020qixian\csv\sample.csv"
    out_sample = r"\\192.168.0.234\nydsj\user\ZSS\2020qixian\csv\sample_test1.csv"
    main(samplefile, out_sample)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
