#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2021/5/14 9:41
# @Author  : zhaoss
# @FileName: weather_forcast_nmc.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
从中国气象台获取未来6天的天气预报
Parameters
http://www.nmc.cn/publish/forecast/AHA/{qixian}.html

"""

import os
import sys
import requests
import time
import json
from datetime import datetime
import psycopg2
from bs4 import BeautifulSoup


headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Host": "www.weather.com.cn",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.182 Safari/537.36"
}
city_dict = {
    'changyuan': '长垣',
    'zhengzhou': '郑州',
    'qixian': '淇县',
    'yongcheng': '永城',
    'xinye': '新野',
}


def geturl(url):
    i = 0
    while i < 3:
        try:
            html = requests.get(url, headers=headers, timeout=30)
            html.encoding = 'utf-8'
            return html.text
        except requests.exceptions.RequestException as e:
            time.sleep(5.0)
            i += 1


def main(http, dst):
    # 获取河南省所有县市天气预报链接
    code_url = 'http://www.nmc.cn/rest/province/AHA?_=1676965986141'
    city_code_str = geturl(code_url)
    city_code_json = json.loads(city_code_str)
    # 获取所有县区的天气预报
    for icity in city_code_json:
        # 抓取详细天气预报
        web = '/'.join([http, icity['url']]) 
        html = geturl(web)
        # 分城市抓取
        city_dst = os.path.join(dst, icity['city'])
        if not os.path.exists(city_dst):
            os.makedirs(city_dst)
        # 解析网页
        bsobj = BeautifulSoup(html, features="lxml")
        # 创建输出文件
        date = datetime.now().strftime("%Y-%m-%d")
        day = datetime.now().strftime("%d")
        dst_file = os.path.join(city_dst, date) + '_detail.txt'
        fj = open(dst_file, 'w', newline='')
        title = ','.join(
            ['day', 'time', 'rain(mm)', 'tem(°C)', 'wind_speed(m/s)', 'wind_direct', 'press(hPa)', 'humidity(%)'])
        fj.write(title)
        fj.write('\n')
        # 获取数据
        forcast_tags = bsobj.find_all('div', {"class": "clearfix pull-left"})
        count = 0
        for tag in forcast_tags:
            s = tag.text.replace('-', '0.0mm').split()
            for idx in range(0, len(s), 8):
                sub_s = s[idx: idx + 8]
                hour = sub_s[0].split('日')
                if len(hour) == 2:
                    day = hour[0]
                    count += 1
                tmp_day = day + '日'
                if count == 7:
                    break
                rain = sub_s[1][:-2]
                tem = sub_s[2][:-1]
                if '0.0mm' in tem:
                    tem = tem.replace('0.0mm', '-')
                wind_speed = sub_s[3][:-3]
                press = sub_s[5][:-3]
                humidity = sub_s[6][:-1]
                out_message = ','.join(
                    [tmp_day, hour[-1], rain, tem, wind_speed, sub_s[4], press, humidity])
                fj.write(out_message)
                fj.write('\n')
        fj.close()
        time.sleep(0.5)
    return None


if __name__ == '__main__':
    # 待抓取地区的网址
    https = "http://www.nmc.cn"
    dst_dir = r"F:\test\weather"
    start_time = time.time()
    main(https, dst_dir)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
