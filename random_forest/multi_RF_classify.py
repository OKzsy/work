#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2020/5/6 15:47
# @Author  : zhaoss
# @FileName: multi_RF_classify.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
使用共享内存，多线程技术利用随机森林方法进行影像分类

Parameters


"""

import os
import sys
import glob
import time
import pickle
import fnmatch
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst

from datablock import DataBlock

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


def get_predict(trees_result, trees_feature, in_data, out_data):
    """
    利用训练好的随机森林模型对样本进行预测
    :param trees_result: 训练好的随机森林模型
    :param trees_feature: 每一颗分类树选择的特征
    :param data_train: 待分类影像
    :return: 对样本的预测结果
    """
    m_tree = len(trees_result)
    rows = in_data.shape[1]
    cols = in_data.shape[2]
    for irow in range(rows):
        for icol in range(cols):
            data_point = in_data[:, irow, icol]
            if np.sum(data_point) == 0:
                continue
            result_i = []
            for itree in range(m_tree):
                clf = trees_result[itree]
                feature = trees_feature[itree]
                data = data_point[feature]
                result_i.append(predict(data, clf))
            u, c = np.unique(np.array(result_i), return_counts=True)
            out_data[irow, icol] = u[np.argmax(c)]
    in_data = None
    return out_data


def main(model, feature, image, out):
    #  加载模型
    with open(model, 'rb') as f:
        trees_result = pickle.load(f)
    with open(feature, 'rb') as f:
        trees_feature = pickle.load(f)
    # 打开待分类影像
    in_ds = gdal.Open(image)
    rpj = in_ds.GetProjection()
    geo = in_ds.GetGeoTransform()
    xsize = in_ds.RasterXSize
    ysize = in_ds.RasterYSize
    oridata = in_ds.ReadAsArray()
    # 创建分类结果
    tif_driver = gdal.GetDriverByName('GTiff')
    out_ds = tif_driver.Create(out, xsize, ysize, 1, gdal.GDT_Byte)
    out_ds.SetProjection(rpj)
    out_ds.SetGeoTransform(geo)


    
    # 为下一版的使用共享内存，多线程留下思路和接口
    out_arr = np.zeros((ysize, xsize), dtype=np.byte) + 200
    # 进行分类
    out_arr = get_predict(trees_result, trees_feature, oridata, out_arr)
    # 写出结果
    out_ds.GetRasterBand(1).WriteArray(out_arr)
    out_ds = None
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
    model_file = r"F:\test_data\dengfeng\model.pkl"
    feature_file = r"F:\test_data\dengfeng\feature.pkl"
    img_file = r"F:\test_data\dengfeng\S2\L2A_20200318_dengfeng_with_veg_index.tif"
    out_file = r"F:\test_data\dengfeng\class\L2A_20200318_dengfeng_class.tif"
    main(model_file, feature_file, img_file, out_file)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
