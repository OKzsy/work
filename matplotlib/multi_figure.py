#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/9/4 13:38
# @Author  : zhaoss
# @FileName: multi_figure.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import sys
import glob
import time
import fnmatch
import numpy as np
import matplotlib.pyplot as plt




def main():
    fig1 = plt.figure('test')
    # 定义x轴
    x = np.linspace(-5, 5, 200)
    # 生成y轴
    y1 = x * 2 + 1
    # 生成第二y轴
    y2 = x ** 2
    plt.xlabel('This is x axis')
    plt.ylabel('This is y axis')
    plt.plot(x, y2)
    plt.show()
    return None


if __name__ == '__main__':
    start_time = time.clock()

    end_time = time.clock()
    main()
    print("time: %.4f secs." % (end_time - start_time))


