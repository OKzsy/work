# -*- coding: utf-8 -*-
"""
Created on Sat Jul  7 10:18:37 2018

@author: 01
"""
#计算均方根误差
import numpy as np
def calculate_rmse(M,pts1,pts2):   #M为参数1，pts1,pts2为参数2
    one=np.ones((pts1.shape[0],1))
    pts2_one=np.c_[pts2,one]
    pts2_t=[]
    for j in range(pts1.shape[0]):
        pts2_t.append(np.dot(M,pts2_one[j]))
    pts2_t=np.array(pts2_t)
    rmse=np.sqrt(np.sum(np.square(pts2_t-pts1))/pts1.shape[0])
    rmse_each=np.sqrt(np.sum(np.square(pts2_t-pts1),axis=1))
    return rmse,rmse_each #rmse,rmse_each分别为参数3，参数4
