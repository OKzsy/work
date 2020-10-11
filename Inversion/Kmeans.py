#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2020/10/10 19:56
# @Author  : zhaoss
# @FileName: Kmeans.py
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
from sklearn.cluster import KMeans
from sklearn import metrics
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def main(file):
    data = np.loadtxt(file, delimiter=',', dtype=np.float32)
    num_clusters = 8
    km_cluster = KMeans(n_clusters=num_clusters, max_iter=300, n_init=10, \
                        init='k-means++', n_jobs=-1)
    result = km_cluster.fit_predict(data)

    print("Predicting result: ", result)

    res = metrics.calinski_harabaz_score(data, result)
    print("calinski_harabaz_score:", res)
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
    data_file = r"F:\tmp\data.csv"
    main(data_file)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))


