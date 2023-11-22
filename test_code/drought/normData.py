#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2023/07/29 17:14
# @Author  : zhaoss
# @FileName: normData.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
按照指定的格式整理数据
Parameters

"""
import os
import time
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def main(vi, norm):
    # 获取非格式化数据
    viFj = open(vi, 'r', encoding='utf-8')
    lines = viFj.read().splitlines()
    # 定义结果字典
    viDict = {}
    for line in lines[1:]:
        data = line.split(',')
        # 获取diffDayg
        diffDay = data[1]
        # 获取yield
        yieldValue = float(data[2])
        # 获取VI
        viValue = data[3]
        if yieldValue in list(viDict.keys()):
            if diffDay in list(viDict[yieldValue].keys()):
                viDict[yieldValue][diffDay] = viValue
            else:
                viDict[yieldValue][diffDay] = viValue
        else:
            viDict[yieldValue] = {diffDay:viValue}
    # 整理输出结果
    # 整理产量
    yieldList = sorted(list(viDict.keys()))
    viList = []
    
    for iyield in yieldList:
        # 获取基本数据
        odata = sorted(viDict[iyield].items(), key=lambda x: float(x[0]))
        iviValue = [x[1] for x in odata]
        sortDiffDay = [x[0] for x in odata]
        viList.append(iviValue)
    viFj.close()
    # 输出结果
    ofj = open(norm, 'w', encoding='utf-8')
    tmpTitle = ['diffDay'] + [str(x) for x in yieldList]
    ofj.write(','.join(tmpTitle))
    ofj.write('\n')
    for i in range(len(sortDiffDay)):
        tmp = [str(sortDiffDay[i])] + [k[i] for k in viList]
        ofj.write(','.join(tmp))
        ofj.write('\n')
        pass
    ofj.close()
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
    viTxt = r"F:\test\ndvi.txt"
    normTxt = r"F:\test\norm_ndvi.txt"
    main(viTxt, normTxt)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))