#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2020/8/29 15:44
# @Author  : zhaoss
# @FileName: multi_prun_numba_train.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import time
import math
import sys
import pickle
import numpy as np
import numba as nb
import multiprocessing as mp
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


@nb.njit()
def cal_gini(data):
    """
    计算给定数据集的gini指数
    :param data: numpy array 数据集
    :return: Gini指数
    """
    # 样本总个数
    total_sample = data.shape[0]
    if total_sample == 0:
        return 0
    max_i = data[0]
    min_i = data[0]
    for i in range(total_sample):
        max_i = max(max_i, data[i])
        min_i = min(min_i, data[i])
    min_i = min(min_i, 0)
    max_i -= min_i
    real_total = max_i + 1
    label_count = np.zeros(real_total)
    for i in range(total_sample):
        tmp = data[i] - min_i
        label_count[tmp] += 1
    gini = 0
    for j in range(real_total):
        gini += (label_count[j] * label_count[j])
    gini = 1 - gini / (total_sample * total_sample)
    return gini


@nb.njit()
def nwhere(data, value):
    # 样本总个数
    total_sample = data.shape[0]
    ge_index = np.zeros(total_sample, dtype=np.uint32)
    lt_index = np.zeros(total_sample, dtype=np.uint32)
    ge_count = 0
    lt_count = 0
    for i in range(total_sample):
        if min(data[i], value) == value:
            ge_index[ge_count] = i
            ge_count += 1
        else:
            lt_index[lt_count] = i
            lt_count += 1
    return ge_index[0:ge_count], ge_count, lt_index[0:lt_count], lt_count


@nb.njit()
def cal_per_value(currentgini, data):
    bestgini = 0.0
    # 样本中的可用特征个数
    feature_num = data.shape[1] - 1
    # 寻找最好的切分属性和切分点
    for fea in range(feature_num):
        # 获取所在fea特征所有可能取得的值
        tmp_feature = data[:, fea]
        feature_values = cyunique(tmp_feature)
        # 对每一个可能的值进行数据集划分，并计算gini指数
        for value in feature_values[0]:
            # 根据fea特征中的值将数据集划分为左右子树
            index1, size1, index2, size2 = nwhere(tmp_feature, value)
            if size1 * size2 == 0:
                continue
            set1 = data[index1, :]
            set2 = data[index2, :]
            # 计算拆分后的gini指数
            nowgini = (size1 * cal_gini(set1[:, -1]) + size2 * cal_gini(set2[:, -1])) / \
                      data.shape[0]
            # 计算gini指数增加量
            gain = currentgini - nowgini
            # 判断此划分是否比当前划分更好
            if gain > bestgini and size1 > 0 and size2 > 0:
                bestgini = gain
                # 最佳切分属性以及最佳切分点
                bestcriteria = [fea, value]
                # 存储切分后的两个数据集
                bestsets = [set1, set2]
    if bestgini == 0.0:
        bestcriteria = [-1, -1]
        tmp_set = np.zeros((3, 3), dtype=data.dtype)
        bestsets = [tmp_set, tmp_set]
        return bestgini, bestcriteria, bestsets
    else:
        return bestgini, bestcriteria, bestsets


def build_tree(data, depth=1):
    node = {'fea': -1,
            'value': None,
            'results': None,
            'right': None,
            'left': None}
    # 增加树的深度变量
    depth += 1
    # 构建决策树，函数返回该决策树的根节点
    if data.shape[0] == 0:
        return node
        # 增加模糊度判断过程
    threshold = 0.95
    lable_jugdment = cyunique(data[:, -1])
    # 判断剩余标签种类个数
    lable_cate = lable_jugdment[0]
    lable_count = lable_jugdment[1]
    max_lable_rate = lable_count.max() / lable_count.sum()
    # 如果数据集中的标签只有一种，直接返回结果
    if lable_cate.shape[0] == 1:
        node['results'] = lable_jugdment
        return node
    # 如果对数据集的划分结果达到要求直接返回结果
    if (max_lable_rate >= threshold) and (depth >= 4):
        lable_count_argsort = np.argsort(lable_count)[::-1]
        lable_cate = lable_cate[lable_count_argsort]
        lable_count = lable_count[lable_count_argsort]
        lable_jugdment = (lable_cate, lable_count)
        node['results'] = lable_jugdment
        return node
    # 计算当前的gini指数
    currentgini = cal_gini(data[:, -1])
    # 计算本次样本中最佳的划分
    bestgini, bestcriteria, bestsets = cal_per_value(currentgini, data)
    # 判断划分是否结束
    if bestgini > 0:
        right = build_tree(bestsets[0], depth=depth)
        left = build_tree(bestsets[1], depth=depth)
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
    # 分别计算精度
    flags = np.unique(data_train[:, -1])
    mat = np.zeros([flags.size, flags.size])
    for ipre in range(len(flags)):
        pre_index = np.where(final_predict == flags[ipre])
        tr_value = data_train[:, -1][pre_index]
        for itr in range(len(flags)):
            tr_flag = flags[itr]
            mat[ipre, itr] = np.where(tr_value == tr_flag)[0].shape[0]
    # 计算混淆矩阵
    # 精度（Precision）代表多分进来，即不属于该标签，被误分为该标签。不要多分，即精度必须高，
    # 保证分为该类的，其可信度较高，但会有本应该分为该类的分为其他类
    # 灵敏度（Sensitivity）代表少分，即本应应该数据该标签，结果部分分为其他标签，不要少分，
    # 即灵敏度必须高，保证是该类的尽量部分为其他类，结果是分为该类的中，有部分本应该是其他类的。
    micro_ppv = np.zeros(len(flags))
    micro_trp = np.zeros(len(flags))
    for iflag in range(len(flags)):
        Tp = mat[iflag, iflag]
        Fp = np.sum(mat[iflag, :]) - Tp
        Fn = np.sum(mat[:, iflag]) - Tp
        Tn = np.sum(mat) - Tp - Fp - Fn

        ppv = Tp / (Tp + Fp)
        micro_ppv[iflag] = ppv
        trp = Tp / (Tp + Fn)
        micro_trp[iflag] = trp
        F1Score = 2 * ppv * trp / (ppv + trp)
        print('The flag is: {}'.format(flags[iflag]))
        print('The Precision is: {:<5.4}'.format(ppv))
        print('The Sensitivity is: {:<5.4}'.format(trp))
        print('The F1-Score is: {:<5.4}'.format(F1Score))
    micro_p = np.average(micro_ppv)
    micro_t = np.average(micro_trp)
    micro_f1 = 2 * micro_p * micro_t / (micro_p + micro_t)
    print('The Micro-F1-Score is: {:<5.4}'.format(micro_f1))
    acc = np.trace(mat) / np.sum(mat)
    print('The Accuracy is: {:<5.4}'.format(acc))
    # 计算kappa系数
    pe_rows = np.sum(mat, axis=0)
    pe_cols = np.sum(mat, axis=1)
    sum_total = sum(pe_cols)
    pe = np.dot(pe_rows, pe_cols) / float(sum_total ** 2)
    po = np.trace(mat) / float(sum_total)
    kappa = (po - pe) / (1 - pe)
    print('The Kappa is: {:<5.4}'.format(kappa))
    return [kappa, acc, micro_f1]


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
    data = np.loadtxt(sample_file, delimiter=',', dtype=np.int16)
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
    # 输出根据混淆矩阵计算得到的混合精度，Kappa, total accuracy, Micro-F1-Score
    Precision = cal_corr_rate(data_verify, result)
    str_pre = [str(round(ipre, 4)) for ipre in Precision]
    corr_rate = '_'.join(str_pre)
    model_name = os.path.splitext(os.path.basename(model_name))[0]
    # 判断输出路径是否存在，不存在创建
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)
    model_file = os.path.join(model_dir, model_name) + '_' + str(tree_num) + '_' + corr_rate + '_mdl.pkl'
    feature_file = os.path.join(model_dir, model_name) + '_' + str(tree_num) + '_' + corr_rate + '_fea.pkl'
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
    samplefile = r"F:\test_data\dengfeng\newsample.csv"
    model_dir = r"E:\MNIST_dataset"
    model_name = 's2_0706_25_nea.pkl'
    for tree_num in range(10, 31, 5):
        for iround in range(3):
            print('Start the {} round of training for {} trees'.format(str(iround + 1), str(tree_num)))
            main(samplefile, model_dir, model_name, tree_num)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
