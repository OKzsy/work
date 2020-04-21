#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/7/23 17:02
# @Author  : zhaoss
# @FileName: AODforLinux.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta
from requests import exceptions
import subprocess
import glob
import ssl
import shutil
import fnmatch
import time
import json
import os
import sys


class RequestError(Exception):
    pass


# CTX = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
USERAGENT = 'tis/download.py_1.0--' + sys.version.replace('\n', '').replace('\r', '')


# USERAGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36'


class Nasa:
    def __init__(self, product="MOD04_L2", collection="61", date=None, latlng=None, save_path=None):
        self.product = product
        self.collection = collection
        self.save_path = save_path
        self.date = date
        self.latlng = 'x' + str(latlng[0]) + 'y' + str(latlng[1]) + ',x' + str(latlng[2]) + 'y' + str(latlng[3])
        self.mm = "38361F0C-3E1B-11E8-916F-FFF9569DBFBA"
        self.headers = {
            'Host': 'ladsweb.modaps.eosdis.nasa.gov',
            'Referer': 'https://ladsweb.modaps.eosdis.nasa.gov/search',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) ' \
                          'Chrome/74.0.3729.131 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest'
        }
        self.url = "https://ladsweb.modaps.eosdis.nasa.gov/api/v1/files/" \
                   "product={0}&collection={1}&dateRanges={2}&areaOfInterest={3}&dayCoverage=true".format(self.product,
                                                                                                          self.collection,
                                                                                                          self.date,
                                                                                                          self.latlng)

    def cal_julday(self):
        # 利用datetime库中的datetime函数的方法快速计算需要日期的儒略日
        year = self.date.split('-')[0]
        month = self.date.split('-')[1]
        day = self.date.split('-')[2]
        current = datetime(int(year), int(month), int(day))
        re_julday = current.timetuple().tm_yday
        return str(re_julday)

    def spider(self):
        resp = requests.get(url=self.url, headers=self.headers)
        if resp.status_code != 200:
            raise RequestError("请求错误,状态码为{}".format(resp.status_code))
        json_data = resp.json()
        # 拼接出文件的网络地质
        year = self.date.split('-')[0]
        source = "https://ladsweb.modaps.eosdis.nasa.gov/" \
                 "archive/allData/{}/{}/{}/{:0>3}".format(self.collection, self.product, year, self.cal_julday())
        return source, json_data


def sync(source, dest, m):
    """synchronize src url with dest directory"""
    headers = {'user-agent': USERAGENT}
    if not m is None:
        headers['Authorization'] = 'Bearer ' + m
    src = source[0]
    files = source[1]
    if not os.path.exists(dest):
        os.makedirs(dest)
    for k, f in files.items():
        filesize = int(f['size'])
        path = os.path.join(dest, f['name'])
        url = src + '/' + f['name']
        if filesize == 0:
            print("error")
            sys.exit(-1)
        else:
            try:
                if not os.path.exists(path):
                    print('downloading: ', path)
                    print('url: ', url)
                    req = requests.get(url, headers=headers)
                    with open(path, 'w+b') as fh:
                        fh.write(req.content)
                else:
                    print('skipping: ', path)
            except exceptions.Timeout as e:
                print('请求超时：' + str(e.strerror))
                sys.exit(-1)
            except exceptions.HTTPError as e:
                print('http请求错误: ' + str(e.strerror))
                sys.exit(-1)
            except IOError as e:
                print("open `%s': %s" % (e.filename, e.strerror), file=sys.stderr)
                sys.exit(-1)
            except TypeError as t:
                print(t)
                sys.exit(-1)
    return 1


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
        elif fnmatch.fnmatch(os.path.basename(mpath), partfileinfo):
            filelist.append(mpath)
        # 如果mpath为子文件夹，则进行递归调用，判断子文件夹下的文件

    return filelist


def hdf2tiff(date, latlng, save_path, stitch_path, aod_dir):
    # 获取所有hdf文件列表
    hdf_files = searchfiles(save_path, partfileinfo="*.hdf")
    # 定义参数文件
    stitch_txt = os.path.join(stitch_path, '6SV', "stitch.prm")
    if os.path.exists(stitch_txt):
        os.remove(stitch_txt)
    if not os.path.exists(aod_dir):
        os.makedirs(aod_dir)
    # 写入参数
    lun_stitch = open(stitch_txt, "w", newline='')
    lun_stitch.write("{}".format('\n'))
    lun_stitch.write("{:<} = {}{}".format("NUM_RUNS", 1, '\n'))
    lun_stitch.write("{}".format('\n'))
    lun_stitch.write("{}{}".format("BEGIN", '\n'))
    lun_stitch.write("{:<} = {}{}".format("NUMBER_INPUTFILES", len(hdf_files), '\n'))
    lun_stitch.write("{:<} = {}{}".format("INPUT_FILENAMES", "|".join(hdf_files), '\n'))
    lun_stitch.write("{:<} = {}{}".format("OBJECT_NAME", "mod04|", '\n'))
    lun_stitch.write("{:<} = {}{}".format("FIELD_NAME", "AOD_550_Dark_Target_Deep_Blue_Combined|", '\n'))
    lun_stitch.write("{:<} = {}{}".format("BAND_NUMBER", 1, '\n'))
    lun_stitch.write(
        "{:<} = ( {} {} ){}".format("SPATIAL_SUBSET_UL_CORNER", float(int(latlng[1]) + 1), float(int(latlng[0])), '\n'))
    lun_stitch.write(
        "{:<} = ( {} {} ){}".format("SPATIAL_SUBSET_LR_CORNER", float(int(latlng[3])), float(int(latlng[2]) + 1), '\n'))
    lun_stitch.write("{:<} = {}{}".format("OUTPUT_OBJECT_NAME", "mod04|", '\n'))
    lun_stitch.write("{:<} = {}{}".format("OUTGRID_X_PIXELSIZE", 0.100104, '\n'))
    lun_stitch.write("{:<} = {}{}".format("OUTGRID_Y_PIXELSIZE", 0.091171, '\n'))
    lun_stitch.write("{:<} = {}{}".format("RESAMPLING_TYPE", "NN", '\n'))
    lun_stitch.write("{:<} = {}{}".format("OUTPUT_PROJECTION_TYPE", "GEO", '\n'))
    lun_stitch.write("{:<} = {}{}".format("ELLIPSOID_CODE", "WGS84", '\n'))
    reprojection_paramenters = '( 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0  )'
    lun_stitch.write("{:<} = {}{}".format("OUTPUT_PROJECTION_PARAMETERS", reprojection_paramenters, '\n'))
    aod_path = os.path.join(aod_dir, date.replace("-", "")) + '.tif'
    lun_stitch.write("{:<} = {}{}".format("OUTPUT_FILENAME", aod_path, '\n'))
    lun_stitch.write("{:<} = {}{}".format("SAVE_STITCHED_FILE", "NO", '\n'))
    lun_stitch.write("{:<} = {}{}".format("OUTPUT_STITCHED_FILENAME", aod_path, '\n'))
    lun_stitch.write("{:<} = {}{}".format("OUTPUT_TYPE", "GEO", '\n'))
    lun_stitch.write("{}{}".format("END", '\n'))
    lun_stitch.write("{}".format('\n'))
    lun_stitch.close()
    # 开始进行转换和镶嵌
    # 更改程序工作路径
    os.chdir(os.path.dirname(stitch_txt))
    subprocess.call('subset_stitch_swath -p stitch.prm', shell=True)
    os.chdir(stitch_path)
    return None


def main(date, latlng, aod_dir):
    # 获取当前工作路径
    function_position = os.path.dirname(os.path.abspath(sys.argv[0]))
    hdf_path = os.path.join(function_position, '6SV', date.replace("-", ""))
    instance = Nasa(date=date, latlng=latlng, save_path=hdf_path)
    # 爬取符合要求的modis产品名称和数据路径
    modis_product = instance.spider()
    # 下载数据
    status = sync(source=modis_product, dest=hdf_path, m=instance.mm)
    if status != 1:
        sys.exit("文件没有下载完全，请重新下载")
    hdf2tiff(date, latlng, hdf_path, function_position, aod_dir)
    return None


if __name__ == '__main__':
    start_time = time.time()
    aod_dir = r"C:\Users\01\Desktop\python+IDL\atm\6SV\tif_aod"
    latlng = [110.369217, 36.354952, 116.650994, 31.400914]
    # 搜索所有已知的hdf文件
    hdf_files = searchfiles(aod_dir, partfileinfo="*.tif")
    # 获得所有日期
    hdf_dates = []
    for ihdf in hdf_files:
        hdf_date = os.path.splitext(os.path.basename(ihdf))[0]
        hdf_dates.append(int(hdf_date))
    # 获取距程序运行最近的日期
    hdf_dates.sort(reverse=True)
    last_date = str(hdf_dates[0])
    last_date_str = '-'.join([last_date[0:4], last_date[4:6], last_date[6:8]])
    last_date_dt = datetime.strptime(last_date_str, "%Y-%m-%d")
    now_dt = datetime.strptime((datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"), "%Y-%m-%d")
    for iday in range((now_dt - last_date_dt).days):
        new_dt = last_date_dt + timedelta(iday + 1)
        day = new_dt.strftime("%Y-%m-%d")
        main(date=day, latlng=latlng, aod_dir=aod_dir)

    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
