# -*- coding: utf-8 -*-
"""
Created on Sat Jul  7 10:20:32 2018

@author: 01
"""


import numpy as np
def var(B):#方差
    n=B.shape[0]
    var=np.sum((B-np.mean(B))**2)/n
    return var
def modify_pan_stat(img1,img3):#拉伸img1，使其具有跟img3相似的分辨率#img1,img3分别为参数1，参数2
    mu3=np.mean(img3)
    mu1=np.mean(img1)
    sigma3=np.sqrt(var(img3))
    sigma1=np.sqrt(var(img1))
    gain=sigma3/sigma1#增益
    print(gain)
    bias=mu3-(gain*mu1)#偏移
    print(bias)
    M_P=img1*gain+bias
    return M_P #参数3
