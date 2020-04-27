#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2020/4/27 9:39
# @Author  : zhaoss
# @FileName: gini.py
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
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


class node:
    """
    cart树的节点类
    """

    def __init__(self, fea=-1, value=None, results=None, right=None, left=None):
        # 用于切分数据集属性的索引
        self.fea = fea
        # 设置划分的值
        self.value = value
        # 存储叶节点所属的类别
        self.results = results
        # 右子树
        self.right = right
        # 左子树
        self.left = left


def cal_gini_index(data):
    """
    计算给定数据集的gini指数
    :param data: numpy array 数据集
    :return: Gini指数
    """
    # 样本总个数
    total_sample = len(data)
    if total_sample == 0:
        return 0
    # 统计样本中不同标签的个数
    label_counts = np.unique(data, return_counts=True)
    # 计算gini系数
    gini = 0
    for label in label_counts[1]:
        gini += label * label
    gini = 1 - gini / (total_sample * total_sample)
    return gini


def build_tree(data):
    """
    构建cart树
    :param data: numpy array 训练样本
    :return: 树的根节点
    """
    # 构建决策树，函数返回该决策树的根节点
    if data.shape[0] == 0:
        return node()
    # 计算当前的gini指数
    currentgini = cal_gini_index(data[:, 0])
    bestgini = 0.0
    # 最佳切分属性以及最佳切分点
    bestcriteria = None
    # 存储切分后的两个数据集
    bestsets = None
    # 样本中的可用特征个数
    feature_num = data.shape[1] - 1
    # 寻找最好的切分属性和切分点
    
    return 1


def main():
    ls = [[1, 1, 1], [1, 1, 1], [0, 1, 0], [0, 0, 1], [0, 0, 1]]
    label_ar = np.array(ls)
    res = cal_gini_index(label_ar[:, 0])
    print(res)
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
