#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/3/7 17:40
# @Author  : zhaoss
# @FileName: test_mkdir.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import sys
import time


def main(tag):
    path = "/mnt/glusterfs/clip"
    file_path = os.path.join(path, tag)
    os.mkdir(file_path)
    return None


if __name__ == '__main__':
    start_time = time.clock()
    flag = sys.argv[1]
    main(flag)
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
