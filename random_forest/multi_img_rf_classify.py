#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2020/5/28 17:40
# @Author  : zhaoss
# @FileName: multi_img_rf_classify.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import sys
import glob
import gc
import time
import pickle
import fnmatch
import numpy as np
import multiprocessing as mp
from osgeo import gdal, ogr, osr, gdalconst

from datablock import DataBlock

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def searchfiles(dirpath, partfileinfo='*', recursive=False):
    """列出符合条件的文件（包含路径），默认不进行递归查询，当recursive为True时同时查询子文件夹"""
    # 定义结果输出列表
    filelist = []
    # 列出根目录下包含文件夹在内的所有文件目录
    pathlist = glob.glob(os.path.join(os.path.sep, dirpath, "*"))
    # 逐文件进行判断
    for mpath in pathlist:
        if os.path.isdir(mpath):
            # 默认不判断子文件夹
            if recursive:
                filelist += searchfiles(mpath, partfileinfo, recursive)
        elif fnmatch.fnmatch(os.path.basename(mpath), partfileinfo):
            filelist.append(mpath)
        # 如果mpath为子文件夹，则进行递归调用，判断子文件夹下的文件

    return filelist


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


def get_predict(trees_result, trees_feature, img_block, IDblock):
    """
    利用训练好的随机森林模型对样本进行预测
    :param trees_result: 训练好的随机森林模型
    :param trees_feature: 每一颗分类树选择的特征
    :param data_train: 待分类影像
    :return: 对样本的预测结果
    """
    # 从共享内存中提取数据
    share_in_data = np.frombuffer(global_in_share, in_dtype).reshape(IN_SHAPE)
    share_out_data = np.frombuffer(global_out_share, out_dtype).reshape(OUT_SHAPE)
    dims_get, dims_put = img_block.block(IDblock)
    in_data = share_in_data[:, dims_get[1]: dims_get[1] + dims_get[3], dims_get[0]: dims_get[0] + dims_get[2]]
    out_data = share_out_data[dims_get[1]: dims_get[1] + dims_get[3], dims_get[0]: dims_get[0] + dims_get[2]]
    # 分类
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
    # 将分类的数据放回共享内存中
    share_out_data[dims_put[3]:dims_put[3] + dims_put[1], dims_put[2]: dims_put[2] + dims_get[2]] = out_data
    in_data = out_data = None
    return 1


def init_pool(in_shared, out_share, in_shape, out_shape, in_dt, out_dt):
    """
    多线程准备函数
    :param in_shared: 原始数据
    :param out_share: 输出数据
    :param in_shape: 原始数据形状
    :param out_shape: 输出数据形状
    :param in_dt: 原始数据类型
    :param out_dt: 输出数据类型
    :return:
    """
    global global_in_share
    global global_out_share
    global IN_SHAPE
    global OUT_SHAPE
    global in_dtype
    global out_dtype
    global_in_share = in_shared
    global_out_share = out_share
    IN_SHAPE = in_shape
    OUT_SHAPE = out_shape
    in_dtype = in_dt
    out_dtype = out_dt


def main(model, feature, in_dir, out_dir):
    imgtype2ctype = {1: ['B', 'uint8'], 2: ['H', 'uint16'], 3: ['h', 'int16'], 4: ['I', 'uint32'], 5: ['i', 'int32'],
                     6: ['f', 'float32'], 7: ['d', 'float64']}
    #  加载模型
    with open(model, 'rb') as f:
        trees_result = pickle.load(f)
    with open(feature, 'rb') as f:
        trees_feature = pickle.load(f)
    files = searchfiles(in_dir, partfileinfo='*.tif')
    for ifile in files:
        # 打开待分类影像
        basename = os.path.splitext(os.path.basename(ifile))[0]
        print(basename)
        in_ds = gdal.Open(ifile)
        rpj = in_ds.GetProjection()
        geo = in_ds.GetGeoTransform()
        xsize = in_ds.RasterXSize
        ysize = in_ds.RasterYSize
        # 创建分类结果
        out = os.path.join(out_dir, basename) + '_class.tif'
        tif_driver = gdal.GetDriverByName('GTiff')
        out_ds = tif_driver.Create(out, xsize, ysize, 1, gdal.GDT_Byte)
        out_ds.SetProjection(rpj)
        out_ds.SetGeoTransform(geo)
        # 将原始数据放进共享内存
        oridata = in_ds.ReadAsArray()
        typecode = in_ds.GetRasterBand(1).DataType
        in_dt = np.dtype(imgtype2ctype[typecode][1])
        in_shape = oridata.shape
        ori_share = mp.RawArray(imgtype2ctype[typecode][0], oridata.ravel())
        oridata = None
        # 为结果创建共享内存
        typecode = out_ds.GetRasterBand(1).DataType
        out_dt = np.dtype(imgtype2ctype[typecode][1])
        out_arr = np.zeros((ysize, xsize), dtype=out_dt) + 200
        out_shape = out_arr.shape
        out_share = mp.RawArray(imgtype2ctype[typecode][0], out_arr.ravel())
        out_arr = None
        # 数据进行分块
        # 引用DataBlock类
        img_block = DataBlock(xsize, ysize, 150, 0)
        numsblocks = img_block.numsblocks
        # 进行多线程分类
        # 确定进程数量
        cpu_count = os.cpu_count()
        tasks = cpu_count if cpu_count <= numsblocks else numsblocks
        # 创建线程池
        pool = mp.Pool(processes=tasks, initializer=init_pool,
                       initargs=(ori_share, out_share, in_shape, out_shape, in_dt, out_dt))
        # 进行分类
        for itask in range(numsblocks):
            pool.apply_async(get_predict, args=(trees_result, trees_feature, img_block, itask))
        pool.close()
        pool.join()
        # 写出结果
        # 从共享内存获取结果
        out_arr = np.frombuffer(out_share, out_dt).reshape(out_shape)
        out_ds.GetRasterBand(1).WriteArray(out_arr)
        in_ds = out_ds = ori_share = out_share = out_arr = None
        gc.collect()
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
    img_dir = r"F:\test_data\dengfeng\S2"
    out_dir = r"F:\test_data\dengfeng\class"
    main(model_file, feature_file, img_dir, out_dir)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
