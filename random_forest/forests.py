#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2020/4/28 11:23
# @Author  : zhaoss
# @FileName: forests.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import sys
import glob
import time
import math
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


def choose_sample(data, k):
    """
    从总体样本集中随机选择样本及特征
    :param data: numpy array 原始样本集
    :param k:选择的特征个数
    :return:被选出来的样本，被选择的特征的索引
    """
    # 确定样本个数和特征个数
    sample_num = data.shape[0]
    feature_num = data.shape[1] - 1
    # 先随机算出m个样本，有放回的抽取（m = sample_num)
    random_sample_index = np.random.choice(sample_num, size=sample_num, replace=True)
    random_sample = data[random_sample_index, :]
    random_sample_index = None
    # 选取k个特征，无放回的选取（k <= feature_num)
    feature_index = np.random.choice(feature_num, size=k, replace=False)
    random_sample_feature = random_sample[:, feature_index]
    data_samples = np.insert(random_sample_feature, k, values=random_sample[:, -1], axis=1)
    random_sample = None
    return data_samples, feature_index


def random_forest_training(data_train, trees_num):
    """
    构建随机森林
    :param data_train: numpy array 训练数据集
    :param trees_num: 分类树的个数
    :return: 每一棵树最好的划分，每一棵树对原始特征的选择
    """
    # 构建每一棵树最好的划分
    trees_result = []
    trees_feature = []
    # 确定样本的维数
    feature_num = data_train.shape[1] - 1
    if feature_num > 2:
        # 设置特征的个数
        k = int(math.log(feature_num, 2)) + 1
    else:
        k = 1
    # 开始构建每一颗树
    for i in range(trees_num):
        # 随机选择m个样本，k个特征
        data_samples, feature = choose_sample(data_train, k)
        # 构建每一颗树
        tree = build_tree(data_samples)
        # 保存训练好的分类树
        trees_result.append(tree)
        # 保存该分类树使用的特征
        trees_feature.append(feature)
    return trees_result, trees_feature


def main():
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
