#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/3/27 19:08
# @Author  : zhaoss
# @FileName: get_movie_top250.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import glob
import requests
from bs4 import BeautifulSoup
import time
import re
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def main(url):
    headers = {
        'Host': 'movie.douban.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'
    }
    # movie_list = []
    for i in range(0, 10):
        link = url + '?start=' + str(i * 25)
        response = requests.get(link, headers=headers, timeout=10)
        status = response.status_code
        print("第{0}页的状态：{1}".format(i + 1, status))
        # 解析网页
        soup = BeautifulSoup(response.text, 'lxml')
        div_list = soup.find_all('div', class_='hd')
        rstr = r'[\/\\\:\*\?\<\>\|]'
        for each in div_list:
            chinese_name = each.a.contents[1].text
            eng_name = each.a.contents[3].text
            new_eng_name = re.sub(rstr, "", eng_name)
            # movie_list.append(movie)
            print("中文名：{0}；英文名:{1}".format(chinese_name, new_eng_name))
    return None


if __name__ == '__main__':
    start_time = time.clock()
    link = 'https://movie.douban.com/top250'
    main(link)
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
