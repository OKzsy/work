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
import datetime
import shutil
import time
import json
import os
import sys


class RequestError(Exception):
    pass


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


def geturl(url, token=None, out=None):
    headers = {
        'Host': 'ladsweb.modaps.eosdis.nasa.gov',
        'Referer': 'https://ladsweb.modaps.eosdis.nasa.gov/search',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) ' \
                      'Chrome/74.0.3729.131 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest'
    }
    if not token is None:
        headers['Authorization'] = 'Bearer ' + token
    try:
        import ssl
        CTX = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        if sys.version_info.major == 2:
            import urllib2
            try:
                fh = urllib2.urlopen(urllib2.Request(url, headers=headers), context=CTX)
                if out is None:
                    return fh.read()
                else:
                    shutil.copyfileobj(fh, out)
            except urllib2.HTTPError as e:
                print('HTTP GET error code: %d' % e.code(), file=sys.stderr)
                print('HTTP GET error message: %s' % e.message, file=sys.stderr)
            except urllib2.URLError as e:
                print('Failed to make request: %s' % e.reason, file=sys.stderr)
            return None

        else:
            from urllib.request import urlopen, Request, URLError, HTTPError
            try:
                fh = urlopen(Request(url, headers=headers), context=CTX)
                if out is None:
                    return fh.read().decode('utf-8')
                else:
                    shutil.copyfileobj(fh, out)
            except HTTPError as e:
                print('HTTP GET error code: %d' % e.code(), file=sys.stderr)
                print('HTTP GET error message: %s' % e.message, file=sys.stderr)
            except URLError as e:
                print('Failed to make request: %s' % e.reason, file=sys.stderr)
            return None

    except AttributeError:
        # OS X Python 2 and 3 don't support tlsv1.1+ therefore... curl
        import subprocess
        try:
            args = ['curl', '--fail', '-sS', '-L', '--get', url]
            for (k, v) in headers.items():
                args.extend(['-H', ': '.join([k, v])])
            if out is None:
                # python3's subprocess.check_output returns stdout as a byte string
                result = subprocess.check_output(args)
                return result.decode('utf-8') if isinstance(result, bytes) else result
            else:
                subprocess.call(args, stdout=out)
        except subprocess.CalledProcessError as e:
            print('curl GET error message: %' + (e.message if hasattr(e, 'message') else e.output), file=sys.stderr)
        return None


def sync(source, dest, tok):
    '''synchronize src url with dest directory'''
    src = source[0]
    files = source[1]
    # use os.path since python 2/3 both support it while pathlib is 3.4+
    for k, f in files.items():
        # currently we use filesize of 0 to indicate directory
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
                    with open(path, 'w+b') as fh:
                        geturl(url, tok, fh)
                else:
                    print('skipping: ', path)
            except IOError as e:
                print("open `%s': %s" % (e.filename, e.strerror), file=sys.stderr)
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
    day = '2019-03-12'
    latlng = 'x110.3692y36.354952,x116.650994y31.400914'
    save_path = r"F:\henanxiaomai\new\20190312"
    main(date=day, latlng=latlng, save_path=save_path)
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
