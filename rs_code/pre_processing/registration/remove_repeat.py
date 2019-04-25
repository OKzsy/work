# -*- coding: utf-8 -*-
"""
Created on Sat Jul  7 10:22:23 2018

@author: 01
"""
import numpy as np
def remove_repeat(data1):#去除重复点对
    for i in range(data1.shape[0]):
        if i==0:
            data1_n=data1[0].reshape(1,4)
        else:
            for j in range(data1_n.shape[0]):
                if (data1[i]==data1_n[j]).all():
                    break
                else:
                    if j==data1_n.shape[0]-1:
                        data1_n=np.r_[data1_n,data1[i].reshape(1,4)]
                    else:
                        continue
    return data1_n
