#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/3/5 10:53
# @Author  : zhaoss
# @FileName: get_aod.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import glob
import time
import math
import fnmatch
import xml.dom.minidom
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def searchfiles(dirpath, partfileinfo='*', recursive=False):
    """列出符合条件的文件（包含路径），默认不进行递归查询，当recursive为True时同时查询子文件夹"""
    # 定义结果输出列表
    filelist = []
    # 列出根目录下包含文件夹在内的所有文件目录
    pathlist = glob.glob(os.path.join(os.path.sep, dirpath, "*"))
    # 逐文件进行判断
    for mpath in pathlist:
        if os.path.isdir(mpath):
            # 默认不判断子文件夹
            if recursive:
                filelist += searchfiles(mpath, partfileinfo, recursive)
        elif fnmatch.fnmatch(mpath, partfileinfo):
            filelist.append(mpath)
        # 如果mpath为子文件夹，则进行递归调用，判断子文件夹下的文件

    return filelist


def file_basename(path, RemoveSuffix=''):
    """去除文件名后部去除任意指定的字符串。"""
    if not os.path.isfile(path):
        raise Exception("The path is not a file!")
    if not RemoveSuffix:
        return os.path.basename(path)
    else:
        basename = os.path.basename(path)
        return basename[:basename.index(RemoveSuffix)]


def GET_XMLELEMENTS(oDocument, IDtxt):
    # 获取指定IDtxt的值
    oNodeList = oDocument.getElementsByTagName(IDtxt)
    # 定义返回的列表
    strDT = []
    if oNodeList.length == 1:
        return oNodeList[0].firstChild.data
    else:
        for node in oNodeList:
            strDT.append(node.firstChild.data)
        return strDT


def GET_XMLELEMENTS(oDocument, IDtxt):
    # 获取指定IDtxt的值
    oNodeList = oDocument.getElementsByTagName(IDtxt)
    # 定义返回的列表
    strDT = []
    if oNodeList.length == 1:
        return oNodeList[0].firstChild.data
    else:
        for node in oNodeList:
            strDT.append(node.firstChild.data)
        return strDT


def get_aod(oDocument, aod_file):
    aod_ds = gdal.Open(aod_file)
    aod_geo = aod_ds.GetGeoTransform()
    aod_inv_geo = gdal.InvGeoTransform(aod_geo)
    # 左上经度
    ID = 'TopLeftLongitude'
    ulx = float(GET_XMLELEMENTS(oDocument, ID))
    # 左上纬度
    ID = 'TopLeftLatitude'
    uly = float(GET_XMLELEMENTS(oDocument, ID))
    # 右下经度
    ID = 'BottomRightLongitude'
    lrx = float(GET_XMLELEMENTS(oDocument, ID))
    # 右下纬度
    ID = 'BottomRightLatitude'
    lry = float(GET_XMLELEMENTS(oDocument, ID))
    extent = [ulx, uly, lrx, lry]
    # 计算在aod影像上的行列号
    off_ulx, off_uly = map(int, gdal.ApplyGeoTransform(aod_inv_geo, extent[0], extent[1]))
    off_drx, off_dry = map(math.ceil, gdal.ApplyGeoTransform(aod_inv_geo, extent[2], extent[3]))
    columns = off_drx - off_ulx
    rows = off_dry - off_uly
    aod = aod_ds.ReadAsArray(off_ulx, off_uly, columns, rows)
    numbers = columns * rows
    spec_num = np.where(aod == -9999)[0].shape[0]
    if spec_num == numbers:
        mean_aod = -9999
    else:
        mean_aod = np.mean(aod[np.where(aod != -9999)]) * 0.001
    aod_ds = None
    return mean_aod


def main(xmlpath, aod):
    # 注册所有gdal的驱动
    gdal.AllRegister()
    gdal.SetConfigOption("gdal_FILENAME_IS_UTF8", "YES")
    # 打开xml文件
    oDocument = xml.dom.minidom.parse(xmlpath).documentElement
    mean_aod = get_aod(oDocument, aod)
    print('The mean AOD is: {}'.format(mean_aod))
    return None


if __name__ == '__main__':
    start_time = time.clock()
    xml_file = r"E:\GF2_PMS2_E112.0_N32.7_20180406_L1A0003106036-MSS2.xml"
    aod_file = r"E:\mypycode\procode\atm\6SV\tif_aod\20180311.tif"
    main(xml_file, aod_file)
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
