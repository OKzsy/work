#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2022/1/18 9:44
# @Author  : zhaoss
# @FileName: factorial.py
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


def func(val):
    if val == 0:
        return 1
    else:
        return val * func(val - 1)


def main(val):
    res = func(val)
    print(res)
    return None


if __name__ == '__main__':
    start_time = time.time()
    n = 5
    main(n)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
