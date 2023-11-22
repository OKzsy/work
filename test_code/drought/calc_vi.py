#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2023/07/28 09:23
# @Author  : zhaoss
# @FileName: calc_vi.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
计算各种指数
Parameters

"""
import os
import time
import glob
import fnmatch
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


class VIGenerator:
    """
    指数生成器,接受一个影像,调用一个通用的函数,分别计算不同的植被指数
    """

    def __init__(self, bandorder) -> None:
        # 影像波段顺序字典
        self.band = bandorder
        # 指数
        self.ndvi = self.__viNdvi
        self.msavi = self.__viMsavi
        self.ndre = self.__viNdre
        self.ttvi = self.__viTTvi
        pass

    def viCalculator(self, imgPath, viOutputPaht, func):
        """
        desc: 指数生成器的通用函数,负责调用其余指数计算的核心函数,
              并将指数的计算结果输出
        """
        # 获取影像基本信息用于输出
        basename = os.path.splitext(os.path.basename(imgPath))[0]
        in_ds = gdal.Open(imgPath)
        rpj = in_ds.GetProjection()
        geo = in_ds.GetGeoTransform()
        xsize = in_ds.RasterXSize
        ysize = in_ds.RasterYSize
        viRes = func(ds=in_ds, bOrder=self.band)
        # 写出数据
        drv = gdal.GetDriverByName("GTiff")
        outfile = os.path.join(viOutputPaht, basename) + \
            '_' + self.__doc2dict(func.__doc__)['name'] + '.tif'
        out_ds = drv.Create(outfile, xsize, ysize, 1, gdal.GDT_Int16)
        out_ds.SetProjection(rpj)
        out_ds.SetGeoTransform(geo)
        out_ds.GetRasterBand(1).WriteArray(viRes)
        out_ds.FlushCache()
        out_ds = in_ds = None

    def __doc2dict(self, doc):
        """
        将函数的注解处理为字典
        """
        doc_lines = doc.split('\n')
        doc_dict = {}
        for line in doc_lines:
            if ':' in line:
                key, value = line.split(':')
            elif '=' in line:
                key, value = line.split('=')
            else:
                # 跳过无效行
                continue
            # 去除键的前后空格
            key = key.strip()
            # 去除值的前后空格
            value = value.strip()
            # 将键值对添加到字典中
            doc_dict[key] = value
        return doc_dict

    def __viNdvi(self, **vikwargs):
        """
        name: ndvi
        desc: 计算归一化植被指数
        parm1: red
        parm2: inf
        """
        # 获取数据
        ds = vikwargs['ds']
        bandList = vikwargs['bOrder']
        red = ds.GetRasterBand(bandList['red']).ReadAsArray().astype(np.int16)
        inf = ds.GetRasterBand(bandList['inf']).ReadAsArray().astype(np.int16)
        # 计算
        ndvi = (((inf - red) / (inf + red + 0.000001)) * 1000).astype(np.int16)
        red = inf = None
        return ndvi

    def __viMsavi(self, **vikwargs):
        """
        name: msavi
        desc: 针对含有红边波段的哨兵数据计算msavi指数
        parm1: red
        parm2: inf
        """
        # 获取数据
        ds = vikwargs['ds']
        bandList = vikwargs['bOrder']
        red = ds.GetRasterBand(bandList['red']).ReadAsArray()
        inf = ds.GetRasterBand(bandList['inf']).ReadAsArray()
        red = red.astype(np.float32) / 10000
        inf = inf.astype(np.float32) / 10000
        msavi = (inf + 0.5 - np.sqrt((inf + 0.5) * (inf + 0.5) - 2 * (inf - red))) * 1000
        msavi = msavi.astype(np.int16)
        red = inf = None
        return msavi

    def __viNdre(self, **vikwargs):
        """
        name: ndre
        desc: 计算归一化植被指数
        parm1: red_edge1
        parm2: inf
        """
        # 获取数据
        ds = vikwargs['ds']
        bandList = vikwargs['bOrder']
        red_edge1 = ds.GetRasterBand(bandList['red_edge1']).ReadAsArray().astype(np.int16)
        inf = ds.GetRasterBand(bandList['inf']).ReadAsArray().astype(np.int16)
        # 计算
        ndre = (((inf - red_edge1) / (inf + red_edge1 + 0.000001)) * 1000).astype(np.int16)
        red_edge1 = inf = None
        return ndre

    def __viTTvi(self, **vikwargs):
        """
        name: ttvi
        desc: 计算LAI的替代指数
        parm1: red_edge2
        parm1: red_edge3
        parm1: red_edge8a
        """
        # 获取数据
        ds = vikwargs['ds']
        bandList = vikwargs['bOrder']
        red_edge2 = ds.GetRasterBand(bandList['red_edge2']).ReadAsArray()
        red_edge3 = ds.GetRasterBand(bandList['red_edge3']).ReadAsArray()
        red_edge8a = ds.GetRasterBand(bandList['red_edge8a']).ReadAsArray()
        red_edge2 = red_edge2.astype(np.float32) / 10000
        red_edge3 = red_edge3.astype(np.float32) / 10000
        red_edge8a = red_edge8a.astype(np.float32) / 10000
        # 计算
        ttvi = 0.5 * ((865 - 740) * (red_edge3 - red_edge2) - (red_edge8a - red_edge2) * (783 - 740))
        ttvi = (ttvi * 1000).astype(np.int16)
        red_edge2 = red_edge3= red_edge8a = None
        return ttvi


def searchfiles(dirpath, partfileinfo='*', recursive=False):
    """列出符合条件的文件(包含路径), 默认不进行递归查询,当recursive为True时同时查询子文件夹"""
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
        elif fnmatch.fnmatch(os.path.basename(mpath), partfileinfo):
            filelist.append(mpath)
        # 如果mpath为子文件夹，则进行递归调用，判断子文件夹下的文件

    return filelist


def main(src, dst):
    bandOrder = {'blue': 1, 'green': 2, 'red': 3, 'inf': 4, 'red_edge1': 5,
                 'red_edge2': 6, 'red_edge3': 7, 'red_edge8a': 8, 'swir': 9, 'cloud': 10}
    
    # 查询所有数据
    # 判断输入的是否为文件
    if os.path.isdir(src):
        rasters = searchfiles(src, partfileinfo='*.tif')
    else:
        rasters = [src]
    # 计算指数
    genobj = VIGenerator(bandOrder)
    for isrc in rasters:
        # 计算ndvi
        tmpdst = os.path.join(dst, 'ndvi')
        genobj.viCalculator(isrc, tmpdst, genobj.ndvi)
        tmpdst = os.path.join(dst, 'msavi')
        genobj.viCalculator(isrc, tmpdst, genobj.msavi)
        tmpdst = os.path.join(dst, 'ndre')
        genobj.viCalculator(isrc, tmpdst, genobj.ndre)
        tmpdst = os.path.join(dst, 'ttvi')
        genobj.viCalculator(isrc, tmpdst, genobj.ttvi)
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
    srcPath = r"F:\test\chanliang\clip\odata"
    dstPath = r"F:\test\chanliang\clip"
    main(srcPath, dstPath)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
