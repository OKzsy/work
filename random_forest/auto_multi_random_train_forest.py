#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2020/7/18 17:38
# @Author  : zhaoss
# @FileName: auto_multi_random_train_forest.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import sys
import glob
import time
import math
import pickle
import fnmatch
import numpy as np
import multiprocessing as mp
from operator import itemgetter
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


class Bar():
    """用于多线程显示进度条"""
    members = 0

    def __init__(self, total):
        self.total = total

    def update(self):
        Bar.members += 1
        progress(Bar.members / self.total)

    def shutdown(self):
        Bar.members = 0


def cal_gini_index(data):
    """
    计算给定数据集的gini指数
    :param data: numpy array 数据集
    :return: Gini指数
    """
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
    node = {'fea': -1,
            'value': None,
            'results': None,
            'right': None,
            'left': None}
    # 构建决策树，函数返回该决策树的根节点
    if data.shape[0] == 0:
        return node
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
            if size1 == 0:
                continue
            set1 = data[index1[0], :]
            index2 = np.where(tmp_feature < value)
            size2 = index2[0].size
            if size2 == 0:
                continue
            set2 = data[index2[0], :]
            # 计算拆分后的gini指数
            nowgini = (size1 * cal_gini_index(
                set1[:, -1]) + size2 * cal_gini_index(set2[:, -1])) / \
                      data.shape[0]
            # 计算gini指数增加量
            gain = currentgini - nowgini
            # 判断此划分是否比当前划分更好
            if gain > bestgini:
                bestgini = gain
                bestcriteria = (fea, value)
                bestsets = (set1, set2)
    # 判断划分是否结束
    if bestgini > 0:
        right = build_tree(bestsets[0])
        left = build_tree(bestsets[1])
        node['fea'] = bestcriteria[0]
        node['value'] = bestcriteria[1]
        node['right'] = right
        node['left'] = left
        return node
    else:
        # 返回当前的类别标签作为最终的类别标签
        node['results'] = np.unique(data[:, -1], return_counts=True)
        return node


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
    random_sample_index = np.random.choice(sample_num, size=sample_num,
                                           replace=True)
    random_sample = data[random_sample_index, :]
    random_sample_index = None
    # 选取k个特征，无放回的选取（k <= feature_num)
    feature_index = np.random.choice(feature_num, size=k, replace=False)
    random_sample_feature = random_sample[:, feature_index]
    data_samples = np.insert(random_sample_feature, k,
                             values=random_sample[:, -1], axis=1)
    random_sample = None
    return data_samples, feature_index


def multi_build_tree(train_data, k):
    # 随机选择m个样本，k个特征
    data_samples, feature = choose_sample(train_data, k)
    # 构建每一颗树
    tree = build_tree(data_samples)
    return tree, feature


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
    # 多线程训练
    tasks = trees_num < os.cpu_count() and trees_num or os.cpu_count()
    pool = mp.Pool(processes=tasks)
    res = []
    # 定义进度条
    bar = Bar(trees_num)
    update = lambda args: bar.update()
    # 开始构建每一颗树
    for i in range(trees_num):
        res.append(pool.apply_async(multi_build_tree, args=(data_train, k),
                                    callback=update))
    pool.close()
    pool.join()
    bar.shutdown()
    for r in res:
        tree, feature = r.get()
        # 保存训练好的分类树
        trees_result.append(tree)
        # 保存该分类树使用的特征
        trees_feature.append(feature)
    return trees_result, trees_feature


def predict(sample, tree):
    """
    对每一个样本进行预测
    :param sample: numpy array 需要预测的样本
    :param tree: 构建好的决策树
    :return: 所属类别
    """
    # 只有树根
    if tree['results'] != None:
        return tree['results'][0][0]
    else:
        # 有左右子树
        val_sample = sample[tree['fea']]
        branch = None
        if val_sample >= tree['value']:
            branch = tree['right']
        else:
            branch = tree['left']
        return predict(sample, branch)


def multi_predict(trees_result, trees_feature, itree, m):
    # 包含标签
    data_train = np.frombuffer(global_in_share, in_dtype).reshape(IN_SHAPE)
    clf = trees_result[itree]
    feature = trees_feature[itree]
    data = data_train[:, feature]
    result_i = []
    for isample in range(m):
        result_i.append(predict(data[isample], clf))
    return result_i


def init_pool(in_shared, in_shape, in_dt):
    """
    多线程准备函数
    :param in_shared: 原始数据
    :param in_shape: 原始数据形状
    :param in_dt: 原始数据类型
    :return:
    """
    global global_in_share
    global IN_SHAPE
    global in_dtype
    global_in_share = in_shared
    IN_SHAPE = in_shape
    in_dtype = in_dt


def get_predict(trees_result, trees_feature, data_train):
    """
    利用训练好的随机森林模型对样本进行预测
    :param trees_result: 训练好的随机森林模型
    :param trees_feature: 每一颗分类树选择的特征
    :param data_train: 训练样本
    :return: 对样本的预测结果
    """
    type2ctype = {'uint8': 'B', 'uint16': 'H', 'int16': 'h', 'uint32': 'I',
                  'int32': 'i',
                  'float32': 'f', 'float64': 'd'}
    # 遍历所有训练好的树，并对应选择建立该树时使用的特征，根据特征从原始数据集中挑选出子数据集
    # ---------------------------------------------------------------------------
    # 结合影像数据量大的特点，采用对对每一个像元遍历所有决策树，然后统计结果
    # ---------------------------------------------------------------------------
    # 实验程序采用样例算法的统计方式
    # 为测试数据创建共享内存，不在进程之间拷贝数据
    typecode = data_train.dtype.name
    dt = data_train.dtype
    shape = data_train.shape
    train_share = mp.RawArray(type2ctype[typecode], data_train.ravel())
    m_tree = len(trees_feature)
    data_train = None
    tasks = m_tree < os.cpu_count() and m_tree or os.cpu_count()
    pool = mp.Pool(processes=tasks, initializer=init_pool,
                   initargs=(train_share, shape, dt))
    m = shape[0]
    result_itree = []
    # 定义进度条
    bar = Bar(m_tree)
    update = lambda args: bar.update()
    for itree in range(m_tree):
        result_itree.append(pool.apply_async(multi_predict, args=(
            trees_result, trees_feature, itree, m), callback=update))
    pool.close()
    pool.join()
    bar.shutdown()
    result_arr = np.array([r.get() for r in result_itree]).T
    result = []
    for line in result_arr:
        result.append(np.argmax(np.bincount(line)))
    return np.array(result)


def cal_corr_rate(data_train, final_predict):
    """
    计算模型的预测准确性
    :param data_train: numpy array 训练样本
    :param final_predict: 预测结果
    :return: 准确性
    """
    m = final_predict.size
    contrast = data_train[:, -1] - final_predict
    accurate = np.where(contrast == 0)[0].shape[0]
    return accurate / m


def save_model(trees_result, trees_feature, model_file, feature_file):
    """
    保存最终模型
    :param trees_result: 训练好的随机森林模型
    :param trees_feature: 每一棵决策树选择的特征
    :param model_file: 模型保存的文件
    :param feature_file: 特征保存的文件
    :return:
    """
    with open(feature_file, 'wb') as f:
        pickle.dump(trees_feature, f)
    with open(model_file, 'wb') as f:
        pickle.dump(trees_result, f)
    return None


def main(sample_file, model_dir, model_name, tree_num):
    # 导入数据
    print("--------------------load data---------------------")
    data = np.loadtxt(sample_file, delimiter=',', dtype=np.int32)
    lines = math.ceil(data.shape[0] * 0.8)
    np.random.shuffle(data)
    data_train, data_verify = data[:lines, :], data[lines:, :]
    data = None
    # 训练random forest 模型
    print("---------------random forest training-------------")
    trees_result, trees_feature = random_forest_training(data_train, tree_num)
    # 得到训练的准确性
    print("---------------get prediction correct rate--------")
    result = get_predict(trees_result, trees_feature, data_verify)
    corr_rate = cal_corr_rate(data_verify, result)
    print(corr_rate)
    corr_rate = str(round(corr_rate, 4))
    model_name = os.path.splitext(os.path.basename(model_name))[0]
    model_file = os.path.join(model_dir, model_name) + '_' + str(tree_num) + '_' +corr_rate + '_mdl.pkl'
    feature_file = os.path.join(model_dir, model_name) + '_' + str(tree_num) + '_' +corr_rate + '_fea.pkl'
    print("--------------------save model---------------------")
    save_model(trees_result, trees_feature, model_file, feature_file)
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
    samplefile = r"/mnt/e/dengfeng/sample.csv"
    model_dir = r"/mnt/e/dengfeng/model"
    model_name = 's2_0706_25_nea.pkl'
    for tree_num in range(10, 31, 5):
        for iround in range(3):
            print('Start the {} round of training for {} trees'.format(str(iround), str(tree_num)))
            main(samplefile, model_dir, model_name, tree_num)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))


