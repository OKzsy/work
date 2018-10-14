#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import glob
import fnmatch
import time


def searchfiles(dirpath, partfileinfo, recursive=False):
    """列出符合条件的文件（包含路径），默认不进行递归查询，当recursive为True时同时查询子文件夹"""
    # 定义结果输出列表
    filelist = []
    # 列出根目录下包含文件夹在内的所有文件目录
    pathlist = glob.glob(os.path.join(os.path.sep, dirpath, "*"))
    # 逐文件进行判断
    for mpath in pathlist:
        if fnmatch.fnmatch(mpath, partfileinfo):
            filelist.append(mpath)
        # 如果mpath为子文件夹，则进行递归调用，判断子文件夹下的文件
        elif os.path.isdir(mpath):
            # 默认不判断子文件夹
            if recursive:
                filelist += searchfiles(mpath, partfileinfo, recursive)
    return filelist


if __name__ == '__main__':
    start_time = time.clock()
    filepath = searchfiles(r"F:\xml", "*E113.2_N33.9*.xml")
    # 获取路径中的路径名称
    dirpath = os.path.dirname(filepath[0])
    # 获取路径中的文件名
    basename = os.path.basename(filepath[0])
    # 获取不带后缀的文件名
    basenamewithoutext = os.path.splitext(basename)[0]
    # 获取截至到任意位置的文件名
    basename_arb = basename[:basename.index("-PAN1.xml")]
    print("路径：", dirpath)
    print("文件名:", basename)
    print("没有后缀的文件名:", basenamewithoutext)
    print("任意位置的文件名:", basename_arb)

    end_time = time.clock()

    print("time: %.3f sec." % (end_time - start_time))
