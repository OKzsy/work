#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2021/1/29 12:44
# @Author  : zhaoss
# @FileName: OCR.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import sys
import glob
import re
import time
import easyocr
from PIL import Image
import fnmatch
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def main(jpg):
    # 创建reader对象
    reader = easyocr.Reader(['ch_sim', 'en'])
    src_files = [file for file in os.listdir(jpg) if file.endswith('.jpg')]
    # 创建输出
    txt_file = os.path.join(jpg, 'res.txt')
    fn = open(txt_file, 'w')
    for ifile in src_files:
        basename = os.path.splitext(ifile)[0]
        print(basename)
        ifile_path = os.path.join(jpg, ifile)
        arr = np.array(Image.open(ifile_path))
        # 读取图像
        result = reader.readtext(arr)
        # 结果
        start_point = 0
        for itest in range(len(result)):
            test = re.split(':|;', result[itest][1])[0]
            if '联' in test:
                start_point = itest
                break
        phone_number = re.split(':|;', result[start_point][1])[-1]
        if not len(phone_number):
            check = True
            while check:
                start_point += 1
                phone_number = re.split(':|;', result[start_point][1])[-1]
                if len(phone_number):
                    check = False
        start_point += 1
        id = re.split(':|;', result[start_point][1])[-1]
        if not len(id):
            check = True
            while check:
                start_point += 1
                id = re.split(':|;', result[start_point][1])[-1]
                if len(id):
                    check = False
        print(phone_number.strip(), id.strip())
        fn.write(','.join([basename.strip(), phone_number.strip(), id.strip()]) + '\n')
        fn.flush()
    fn.close()
    return None


if __name__ == '__main__':
    # 支持中文路径
    gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
    # 支持中文属性字段
    gdal.SetConfigOption("SHAPE_ENCODING", "GBK")
    # 注册所有ogr驱动
    ogr.RegisterAll()
    # 注册所有gdal驱动
    gdal.AllRegister()
    start_time = time.time()
    jpg_file = r"F:\shiqiao\team2\id"
    main(jpg_file)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
