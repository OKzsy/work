#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2021/3/3 10:07
# @Author  : zhaoss
# @FileName: get_weather_postsql.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
从中国天气网爬取未来15天长垣地区的天气预报

Parameters
http://www.weather.com.cn/weather/101180308.shtml

"""
import os
import sys
import requests
import time
import datetime
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
    'changyuan': '101180308',
    'qixian': '101181203',
    'zhengzhou': '101180101'
}

city_name = {
    'changyuan': '长垣',
    'zhengzhou': '郑州',
    'qixian': '淇县',
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


def parse_7d(obj):
    # 查找包含天气内容的父标签
    tag_7d = obj.find("div", {"id": "7d", "class": "c7d"})
    # 获取天气
    weather_tag = tag_7d.find("ul", {"class": "t clearfix"})
    messages = []
    for child in weather_tag.findAll('li'):
        one_day_messages = []
        # 提取日期
        one_day_messages.append(child.h1.get_text()[:-4])
        # 提取天气情况
        wea = child.find("", {"class": "wea"}).get_text()
        one_day_messages.append(wea)
        # 提取温度
        tem = child.find("", {"class": "tem"})
        maxtem = tem.span.get_text()
        mintem = tem.i.get_text()
        one_day_messages.append(maxtem)
        one_day_messages.append(mintem[:-1])
        # 提取风向和风力
        win = child.find("", {"class": "win"})
        # 提取风向信息
        for direct in win.em.findAll("span"):
            one_day_messages.append(direct.get('title'))
        # 提取风力
        win_force = win.i.get_text()
        one_day_messages.append(win_force)
        messages.append(one_day_messages)
    return messages


def parse_15d(obj):
    # 查找包含天气内容的父标签
    tag_15d = obj.find("div", {"id": "15d", "class": "c15d"})
    # 获取天气
    weather_tag = tag_15d.find("ul", {"class": "t clearfix"})
    messages = []
    for child in weather_tag.findAll('li'):
        one_day_messages = []
        # 提取日期
        one_day_messages.append(child.span.get_text()[2:][1:-1])
        # 提取天气情况
        wea = child.find("", {"class": "wea"}).get_text()
        one_day_messages.append(wea)
        # 提取温度
        tem = child.find("", {"class": "tem"})
        tem_str = tem.text.split('/')
        maxtem = tem_str[0][:-1]
        mintem = tem_str[1][:-1]
        one_day_messages.append(maxtem)
        one_day_messages.append(mintem)
        # 提取风向信息
        win_direct = child.find("", {"class": "wind"}).text
        win_directs = win_direct.split('转')
        if len(win_directs) == 2:
            one_day_messages.append(win_directs[0])
            one_day_messages.append(win_directs[1])
        else:
            one_day_messages.append(win_directs[0])
            one_day_messages.append(win_directs[0])
        # 提取风力
        win_force = child.find("", {"class": "wind1"})
        one_day_messages.append(win_force.text)
        messages.append(one_day_messages)
    return messages


def main(http, city, code):
    # 抓取7天内天气网页
    web = '/'.join([http, 'weather', code]) + '.shtml'
    html = geturl(web)
    if html == None:
        raise Exception("抓取网页失败")
    bsobj = BeautifulSoup(html, features="lxml")
    # 获取更新时间
    conn = psycopg2.connect(database="WebGis", user="sa", password="Nydsj@222", host="192.168.0.250", port="5432")
    cur = conn.cursor()
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    update_time = bsobj.find("input", {"id": "update_time"}).get("value")
    select_str = "SELECT * FROM weather_forecast " \
                 "WHERE date1='{date}' AND shijian='{time}' AND city='{city}'".format(date=date,
                                                                                      time=update_time,
                                                                                      city=city_name[city])
    cur.execute(select_str)
    content = cur.fetchall()
    if len(content) != 0:
        conn.close()
        return None
    # 解析网页
    content_7d = parse_7d(bsobj)
    # 抓取15天内天气网页
    web = '/'.join([http, 'weather15d', code]) + '.shtml'
    html = geturl(web)
    if html == None:
        raise Exception("抓取网页失败")
    bsobj = BeautifulSoup(html, features="lxml")
    content_15d = parse_15d(bsobj)
    # 保存天气信息
    idate = 0
    for imessage in content_7d:
        riqi = (datetime.datetime.now() + datetime.timedelta(days=idate)).strftime('%Y-%m-%d')
        insert_str = "INSERT INTO weather_forecast VALUES ('{date_str}','{time_str}','{riqi}','{city}','{weather}'," \
                     "'{maxtem}','{mintem}','{wind_dir1}','{wind_dir2}','{wind_level}')".format(date_str=date,
                                                                                                time_str=update_time,
                                                                                                riqi=riqi,
                                                                                                city=city_name[city],
                                                                                                weather=imessage[1],
                                                                                                maxtem=imessage[2],
                                                                                                mintem=imessage[3],
                                                                                                wind_dir1=imessage[4],
                                                                                                wind_dir2=imessage[5],
                                                                                                wind_level=imessage[6])
        idate += 1
        cur.execute(insert_str)
        conn.commit()
    for imessage in content_15d:
        riqi = (datetime.datetime.now() + datetime.timedelta(days=idate)).strftime('%Y-%m-%d')
        insert_str = "INSERT INTO weather_forecast VALUES ('{date_str}','{time_str}','{riqi}','{city}','{weather}'," \
                     "'{maxtem}','{mintem}','{wind_dir1}','{wind_dir2}','{wind_level}')".format(date_str=date,
                                                                                                time_str=update_time,
                                                                                                riqi=riqi,
                                                                                                city=city_name[city],
                                                                                                weather=imessage[1],
                                                                                                maxtem=imessage[2],
                                                                                                mintem=imessage[3],
                                                                                                wind_dir1=imessage[4],
                                                                                                wind_dir2=imessage[5],
                                                                                                wind_level=imessage[6])
        idate += 1
        cur.execute(insert_str)
        conn.commit()
    conn.close()
    return None


if __name__ == '__main__':
    # 待抓取地区的网址
    https = "http://www.weather.com.cn"
    for icity, icode in city_dict.items():
        main(https, icity, icode)
