#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2023/08/04 11:50
# @Author  : zhaoss
# @FileName: pam.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
k-中心点聚类算法
Parameters

"""
import os
import time
import random
import numpy as np


def euclidean_distance(errMatrix: np.ndarray, matrixDim: int) -> np.ndarray:
    # 计算欧拉距离
    # 只有一个特征
    if matrixDim == 1:
        eudis = np.abs(errMatrix)
    # 大于1个特征
    else:
        eudis = np.linalg.norm(errMatrix, ord=2, axis=0)
    return eudis
    

def pam(data: np.ndarray, k: int, feats: list):
    """
    name:中心聚类算法的一种,pam聚类算法
    parm1-data:代聚类的数据,可以是多维,numpy数组形式
    parm2-k:代聚成簇的个数
    """
    # 初始化簇中心
    dataSize = data.shape
    # 确定初始聚类中心
    medoids = random.sample(range(dataSize[1]), k)
    medoids = sorted(medoids)
    print(medoids)
    # medoids = [4, 6]
    
    # 聚类
    while True:
        # 初始聚类
        featNum = len(feats)
        clusters = np.zeros((k, dataSize[1]), dtype=np.float32)
        # 创建临时误差矩阵
        tmpErr = np.zeros((featNum, dataSize[1]), dtype=np.float32)
        for ik in range(k):
            ifeat = 0
            for feat in feats:
                tmpErr[ifeat, :] = data[feat, :] - data[feat, medoids[ik]]
                ifeat += 1
                pass
            # 计算欧拉距离
            clusters[ik, :] = euclidean_distance(tmpErr, featNum)
        tmpErr = None
        pass
        cluster = np.argmin(clusters, axis=0)
        print(cluster)
        # 对每一个簇,找到使得SSW最小的样本点作为簇的新medoid
        newMedoids = []
        allssw = []
        for ik in range(k):
            medoid = medoids[ik]
            ikIdx = np.where(cluster == ik)
            ikIdxNum = ikIdx[0].shape[0]
            ssw = np.sum(clusters[ik, ikIdx])
            # 创建临时误差矩阵
            tmpErr = np.zeros((featNum, ikIdxNum), dtype=np.float32)
            for idx in ikIdx[0]:
                ifeat = 0
                for feat in feats:
                    tmpErr[ifeat, :] = data[feat, ikIdx] - data[feat, idx]
                    ifeat += 1
                newssw = np.sum(euclidean_distance(tmpErr, featNum))
                if newssw < ssw:
                    ssw = newssw
                    medoid = idx
            tmpErr = None
            newMedoids.append(medoid)
            allssw.append(ssw)
            
        
        if newMedoids == medoids:
            print(sum(allssw))
            print(medoids)
            break
        medoids = newMedoids
    return cluster


def main():
    odata = [(2, 6), (8, 4), (3, 8), (4, 7), (6, 2),
             (6, 4), (7, 3), (7, 4), (8, 5), (7, 6)]
    odataList = [[x[0] for x in odata]]
    odataList.append([x[1] for x in odata])
    # 转换为数组
    dataArr = np.array(odataList)
    # 将三维数据输入转换为二维,第一维度为特征维
    dataSize = dataArr.shape
    ndims = dataArr.ndim
    if ndims > 2:
        dataArr = dataArr.reshape(dataSize[0], -1)
    # 目标簇数
    k = 2
    # 选择依据那些特征聚类
    featIdx = list(range(0, 2))
    # featIdx = [1]
    # 多次聚类选择最优结果, 待完善
    res = pam(dataArr, k, featIdx)
    print(res)


    return None


if __name__ == '__main__':
    start_time = time.time()
    main()
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
