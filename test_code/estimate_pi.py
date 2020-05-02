#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2020/3/13 14:43
# @Author  : zhaoss
# @FileName: estimate_pi.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import sys
import glob
import time
import fnmatch
import numpy as np
import random
from multiprocessing import Pool
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def estimate_nbr_points_in_quarter_circle(nbr_estimates):
    nbr_trials = 0
    for step in range(int(nbr_estimates)):
        x = random.uniform(0, 1)
        y = random.uniform(0, 1)
        is_in_unit_circle = x * x + y * y <= 1.0
        nbr_trials += is_in_unit_circle
    return nbr_trials


def main():
    nbr_samples_in_total = 1e8
    nbr_parallel = 8
    pool = Pool(processes=nbr_parallel)
    nbr_samples_per_worker = nbr_samples_in_total / nbr_parallel
    print("Making {}".format(nbr_samples_per_worker))
    nbr_trials_per_process = [nbr_samples_per_worker] * nbr_parallel
    t1 = time.time()
    nbr_in_unit = pool.map(estimate_nbr_points_in_quarter_circle, nbr_trials_per_process)
    pi_estimate = sum(nbr_in_unit) * 4 / nbr_samples_in_total
    print("estimate pi {} ".format(pi_estimate))
    print("Delta:{}".format(time.time() - t1))
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

    main()
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
