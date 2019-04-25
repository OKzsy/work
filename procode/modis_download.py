#!/usr/bin/env python

# script supports either python2 or python3
#
# Attempts to do HTTP Gets with urllib2(py2) urllib.requets(py3) or subprocess
# if tlsv1.1+ isn't supported by the python ssl module
#
# Will download csv or json depending on which python module is available
#

from __future__ import (division, print_function, absolute_import, unicode_literals)

import argparse
import os
import os.path
import shutil
import sys
import requests
from functools import partial
import multiprocessing.dummy as mp

try:
    from StringIO import StringIO  # python2
except ImportError:
    from io import StringIO  # python3

################################################################################


USERAGENT = 'tis/download.py_1.0--' + sys.version.replace('\n', '').replace('\r', '')


class RequestError(Exception):
    pass


class Nasa:
    def __init__(self, day=None, latlng=None):
        self.headers = {
            'Host': 'ladsweb.modaps.eosdis.nasa.gov',
            'Referer': 'https://ladsweb.modaps.eosdis.nasa.gov/search/order/4/MOD04_L2--61/'
                       '2019-02-12/D/109.6,32.9,117.9,26.2',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/73.0.3683.75 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
        }
        self.url = "https://ladsweb.modaps.eosdis.nasa.gov/api/v1/files/" \
                   "product=MOD04_L2&collection=61&dateRanges={}&areaOfInterest={}&dayCoverage=true".format(day, latlng)

    def spider(self):
        resp = requests.get(url=self.url, headers=self.headers)
        if resp.status_code != 200:
            raise RequestError("请求错误,状态码为{}".format(resp.status_code))
        json_data = resp.json()
        # 获取符合要求的文件名字
        name = json_data[list(json_data.keys())[0]]['name']
        # 拼接出文件的网络地质
        lis = name.split(".")
        loc = lis[3][1:]
        year = lis[1].lstrip('A')[:4]
        code = lis[1].lstrip('A')[4:]
        source = "https://ladsweb.modaps.eosdis.nasa.gov/" \
                 "archive/allData/{}/MOD04_L2/{}/{}".format(loc, year, code)
        return source, json_data


def multi_down(sourc, ds, token, file):
    # currently we use filesize of 0 to indicate directory
    filesize = int(file['size'])
    path = os.path.join(ds, file['name'])
    url = sourc + '/' + file['name']
    if filesize == 0:
        try:
            print('creating dir:', path)
            os.mkdir(path)
            sync(sourc + '/' + file['name'], path, token)
        except IOError as e:
            print("mkdir `%s': %s" % (e.filename, e.strerror), file=sys.stderr)
            sys.exit(-1)
    else:
        try:
            if not os.path.exists(path):
                print('downloading: ', path)
                print('downloading: ', url)
                with open(path, 'w+b') as fh:
                    geturl(url, token, fh)
            else:
                print('skipping: ', path)
        except IOError as e:
            print("open `%s': %s" % (e.filename, e.strerror), file=sys.stderr)
            sys.exit(-1)

    return None


def geturl(url, token=None, out=None):
    headers = {'user-agent': USERAGENT}
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


################################################################################


DESC = "This script will recursively download all files if they don't exist from a LAADS URL and stores them to the specified path"


def sync(src, dest, tok, files):
    '''synchronize src url with dest directory'''
    # use os.path since python 2/3 both support it while pathlib is 3.4+
    pool = mp.Pool(processes=4)
    func = partial(multi_down, src, dest, tok)
    for k, ifile in files.items():
        res = pool.apply_async(func, args=(ifile,))
    pool.close()
    pool.join()
    return 0


def _main():
    day = '2018-03-09'
    latlng = 'x110.3692y36.354952,x116.650994y31.400914'
    instance = Nasa(day=day, latlng=latlng)
    source, name_json = instance.spider()
    destination = r"F:\henanxiaomai\new\20180707"
    token = '38361F0C-3E1B-11E8-916F-FFF9569DBFBA'
    if not os.path.exists(destination):
        os.makedirs(destination)
    return sync(source, destination, token, name_json)


if __name__ == '__main__':
    try:
        sys.exit(_main())
    except KeyboardInterrupt:
        sys.exit(-1)
