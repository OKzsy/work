# -*- coding: utf-8 -*-
"""
Created on Sat Jul  7 10:27:04 2018

@author: 01
"""
import numpy as np
def data_common(data,data1):#求两种方法下的公共匹配点对#data,data1分别为参数1，参数2
    a=0
    data_c=[]
    for i in range(data1.shape[0]):
        for j in range(data.shape[0]):
            if (data1[i]==data[j]).all():
                print(data1[i])
                data_c.append(data1[i])
                a+=1
            else:
                continue
    data_c=np.array(data_c)
    return data_c #参数3
