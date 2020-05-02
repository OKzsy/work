#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/5/5 15:47
# @Author  : zhaoss
# @FileName: Modis_download.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

from bs4 import BeautifulSoup
import requests
from requests import exceptions
import datetime
import shutil
import time
import json
import os
import sys


class RequestError(Exception):
    pass


USERAGENT = 'tis/download.py_1.0--' + sys.version.replace('\n', '').replace('\r', '')
# USERAGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36'


class Nasa:
    def __init__(self, product="MOD04_L2", collection="61", date=None, latlng=None, save_path=None):
        self.product = product
        self.collection = collection
        self.save_path = save_path
        self.date = date
        self.latlng = latlng
        self.token = "38361F0C-3E1B-11E8-916F-FFF9569DBFBA"
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
        current = datetime.datetime(int(year), int(month), int(day))
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


def sync(source, dest, tok):
    """synchronize src url with dest directory"""
    headers = {'user-agent': USERAGENT,
               # "Referer": "https://ladsweb.modaps.eosdis.nasa.gov/archive/allData",
               "Referer": source[0] + '/',
               "Host": "ladsweb.modaps.eosdis.nasa.gov"}
    if not tok is None:
        headers['Authorization'] = 'Bearer ' + tok
    src = source[0]
    files = source[1]
    if not os.path.exists(save_path):
        os.makedirs(save_path)
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
    return 0


def main(date, latlng, save_path):
    instance = Nasa(date=date, latlng=latlng, save_path=save_path)
    # 爬取符合要求的modis产品名称和数据路径
    modis_product = instance.spider()
    # 下载数据
    sync(source=modis_product, dest=save_path, tok=instance.token)
    return None


if __name__ == '__main__':
    start_time = time.clock()
    day = '2020-02-09'
    latlng = 'x110.369217y36.354952,x116.650994y31.400914'
    # latlng = 'x105.285347y32.203355,x110.194193y28.16
    save_path = os.path.join(r"F:\test_modis", day.replace("-", ""))
    main(date=day, latlng=latlng, save_path=save_path)
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
