#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2021/2/22 18:04
# @Author  : zhaoss
# @FileName: get_observe_data.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
从中国天气网爬取长垣地区当天的真实天气情况

Parameters
http://www.weather.com.cn/weather/101180308.shtml

"""
import os
import re
import json
import time
import requests
import datetime

headers = {
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Cookie": "f_city=%E6%B5%8E%E5%8D%97%7C101120101%7C; Hm_lvt_080dabacb001ad3dc8b9b9049b36d43b=1650790859,1650793582,1650934788,1652838859",
    "Host": "d1.weather.com.cn",
    "If-Modified-Since": "Wed, 22 Feb 2023 01:27:31 GMT",
    "If-None-Match": "63f56f83-d5b2",
    "Proxy-Connection": "keep-alive",
    "Referer": "http://www.weather.com.cn/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
}


def main():
    init_minute = 130
    end = True
    count = 0
    while end:
        # 获取当前系统时间
        today = datetime.datetime.now() - datetime.timedelta(minutes=init_minute)  # 获取GMT时间并减去70分钟
        delat_today = today.strftime("%Y%m%d%H%M")  # 时间格式化
        # 分钟向下取整
        delat_today_list = list(delat_today)
        delat_today_list[-1] = "0"
        delat_today = "".join(delat_today_list)
        url = 'http://d1.weather.com.cn/newwebgis/radar/5m/QPFRef_' + delat_today + '.png'
        html = requests.get(url, headers=headers)
        print(html.status_code)
        new_name = r'F:\test\weather'
        with open(new_name + '\\' + delat_today + '.png', 'wb') as f:
            f.write(html.content)
        if count == 23:
            end = False
        else:
            init_minute -= 10
            count += 1

    return None


if __name__ == '__main__':
    # 待抓取地区的网址
    main()
