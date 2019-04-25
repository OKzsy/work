# -*- coding: utf-8 -*-
"""
Created on Sat Jul  7 10:17:40 2018

@author: 01
"""
#最小二乘法计算仿射变换
import numpy as np
def least_square_method(pts1,pts2): #pts1,pts2为参数1
    U=pts1[:,0]
    V=pts1[:,1]
    num=pts1.shape[0]
    one=np.ones((num,1))
    pts2_one=np.c_[pts2,one]
    vec1=np.linalg.inv(np.transpose(pts2_one).dot(pts2_one)).dot(np.transpose(pts2_one)).dot(U)
    vec2=np.linalg.inv(np.transpose(pts2_one).dot(pts2_one)).dot(np.transpose(pts2_one)).dot(V)
    return vec1,vec2 #vec1,vec2为参数2