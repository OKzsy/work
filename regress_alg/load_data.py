#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2022/1/19 13:53
# @Author  : zhaoss
# @FileName: load_data.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
用于从文件中加载用于回归拟合的数据

Parameters


"""

import os
from re import T
import sys
import glob
import time
import fnmatch
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt


def load_data(txt):
    # 加载样本呢数据，样本文件中保函样本特征和样本标签(最后一列）
    data = np.loadtxt(txt, delimiter='\t')
    # 线性回归模型为
    # y = b + sum[1, n](wi * xi)
    # 设定x0 = 1, 则线性回归模型为
    # y = sum[0, n](wi * xi)
    # 其中x0用以模拟b
    feature = np.ones_like(data)
    feature[:, 1:] = data[:, :-1]
    label = data[:, -1]
    # 因为涉及到矩阵求逆等运算,所以返回数组的矩阵形式
    return np.mat(feature), np.mat(label).T

def least_square(feature, label):
    """
    最小二乘拟合
    feature(mat):样本特征
    label(mat):样本标签
    """
    w = (feature.T * feature).I *feature.T * label
    return w

def main(src):
    feature, label = load_data(src)
    w = least_square(feature, label)
    feat, lab = np.loadtxt(src, unpack=True)
    plab = feature * w
    error = (label - feature * w).T * (label - feature * w)
    print('error:{}'.format(error))
    plt.scatter(feat, lab)
    plt.plot(feat, plab)
    plt.show()
    pass


if __name__ == '__main__':
    start_time = time.time()
    txt_file = r"F:\test\data.txt"
    main(txt_file)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
