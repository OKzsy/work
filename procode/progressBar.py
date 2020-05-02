#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/9/9 10:14
# @Author  : zhaoss
# @FileName: progressBar.py
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
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def my_progress(complete, message=None, progressArg=0.025):
    if not hasattr(my_progress, 'last_progress'):
        if not message == None:
            sys.stdout.write(message)
        else:
            sys.stdout.write('0')
        sys.stdout.flush()
        my_progress.last_progress = 0
    if complete >= 1:
        sys.stdout.write('100 - done\n')
        del my_progress.last_progress
    else:
        test = divmod(complete, progressArg)
        progress = divmod(complete, progressArg)[0]
        while my_progress.last_progress < progress:
            if progress % 4 == 0:
                sys.stdout.write(str(int(progress / 4 * 10)))
                sys.stdout.flush()
                my_progress.last_progress += 1
            else:
                sys.stdout.write('.')
                sys.stdout.flush()
                my_progress.last_progress += 1


def main():
    total = 100
    for j in range(1, 11):
        for i in range(1, 101):
            my_progress(i / total)
    #     my_progress(j / 10, "cate2")

    # for j in range(1, 11):
    #     for i in range(1, 101):
    #         progress(i / total, "cate1")
    #     progress(j / 10, "cate2")


if __name__ == '__main__':
    start_time = time.clock()

    end_time = time.clock()
    main()
    print("time: %.4f secs." % (end_time - start_time))


