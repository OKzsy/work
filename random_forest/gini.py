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
    gini = np.sum(label_counts[1] * label_counts[1])
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
    currentgini = cal_gini_index(data[:, -1])
    bestgini = 0.0
    # 最佳切分属性以及最佳切分点
    bestcriteria = None
    # 存储切分后的两个数据集
    bestsets = None
    # 样本中的可用特征个数
    feature_num = data.shape[1] - 1
    # 寻找最好的切分属性和切分点
    for fea in range(feature_num):
        # 获取所在fea特征所有可能取得的值
        tmp_feature = data[:, fea]
        feature_values = np.unique(tmp_feature)
        # 对每一个可能的值进行数据集划分，并计算gini指数
        for value in feature_values:
            # 根据fea特征中的值将数据集划分为左右子树
            index1 = np.where(tmp_feature >= value)
            size1 = index1[0].size
            set1 = data[index1[0], :]
            index2 = np.where(tmp_feature < value)
            size2 = index2[0].size
            set2 = data[index2[0], :]
            if size1 * size2 == 0:
                continue
            # 计算拆分后的gini指数
            nowgini = (size1 * cal_gini_index(set1[:, -1]) + size2 * cal_gini_index(set2[:, -1])) / data.shape[0]
            # 计算gini指数增加量
            gain = currentgini - nowgini
            # 判断此划分是否比当前划分更好
            if gain > bestgini and size1 > 0 and size2 > 0:
                bestgini = gain
                bestcriteria = (fea, value)
                bestsets = (set1, set2)
    # 判断划分是否结束
    if bestgini > 0:
        right = build_tree(bestsets[0])
        left = build_tree(bestsets[1])
        return node(fea=bestcriteria[0], value=bestcriteria[1], right=right, left=left)
    else:
        # 返回当前的类别标签作为最终的类别标签
        return node(results=np.unique(data[:, -1], return_counts=True))


def predict(sample, tree):
    """
    对每一个样本进行预测
    :param sample: numpy array 需要预测的样本
    :param tree: 构建好的决策树
    :return: 所属类别
    """
    # 只有树根
    if tree.results != None:
        return tree.results[0][0]
    else:
        # 有左右子树
        val_sample = sample[tree.fea]
        branch = None
        if val_sample >= tree.value:
            branch = tree.right
        else:
            branch = tree.left
        return predict(sample, branch)


def main():
    ls = [[1, 1, 1], [1, 1, 1], [1, 0, 0], [0, 1, 0], [0, 1, 0]]
    label_ar = np.array(ls)
    tree = build_tree(label_ar)
    sample = np.array([[[0, 1, 1], [1, 0, 0], [1, 0, 0]], [[0, 0, 1], [1, 1, 0], [1, 1, 0]]])
    for irow in range(3):
        for icol in range(3):
            tmp_sample = sample[:, irow, icol]
            res = predict(tmp_sample, tree)
            print(res)


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
