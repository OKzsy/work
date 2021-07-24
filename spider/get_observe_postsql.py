#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2021/3/4 14:50
# @Author  : zhaoss
# @FileName: get_observe_postsql.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
从中国天气网爬取长垣地区当天的真实天气情况

Parameters
http://www.weather.com.cn/weather/101180308.shtml

"""
import re
import json
import time
import psycopg2
import requests
import datetime

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


def save_file(start, end, dst, dt, tem, humidity, rain, wind_angle, wind_direct, wind_level, aqi):
    miss_time = dt[start: end]
    miss_tem = tem[start: end]
    miss_humidity = humidity[start: end]
    miss_rain = rain[start: end]
    miss_wind_angle = wind_angle[start: end]
    miss_wind_direct = wind_direct[start: end]
    miss_wind_level = wind_level[start: end]
    miss_aqi = aqi[start: end]
    # 连接数据库
    conn = psycopg2.connect(database="weather_test", user="sa", password="Nydsj@222", host="192.168.0.250", port="5432")
    cur = conn.cursor()
    # 选择数据
    select_str = "SELECT * FROM weather_collect " \
                 "WHERE date1='{date}' AND city='{city}' ORDER BY time_h ASC".format(date=dst[0],
                                                                                     city=dst[1])
    cur.execute(select_str)
    content = cur.fetchall()
    # 获取文件内容检查并更新
    if len(content) > 0:
        last_time = content[-1][2]
        check_point = miss_time.index(last_time)
        # 更新最后一条数据的aqi
        update_str = "UPDATE weather_collect SET aqi='{aqi}' " \
                     "WHERE date1='{date}' AND city='{city}' AND time_h={time}".format(aqi=miss_aqi[check_point],
                                                                                       date=dst[0],
                                                                                       city=dst[1],
                                                                                       time=last_time)
        cur.execute(update_str)
        conn.commit()
        for i in range(check_point + 1, len(miss_time)):
            insert_str = "INSERT INTO weather_collect VALUES ('{date_str}','{city}','{time}','{tem}','{humidity}'," \
                         "'{rain}','{wind_angle}','{wind_direct}','{wind_level}','{aqi}')".format(date_str=dst[0],
                                                                                                  city=dst[1],
                                                                                                  time=miss_time[i],
                                                                                                  tem=miss_tem[i],
                                                                                                  humidity=
                                                                                                  miss_humidity[i],
                                                                                                  rain=miss_rain[i],
                                                                                                  wind_angle=
                                                                                                  miss_wind_angle[i],
                                                                                                  wind_direct=
                                                                                                  miss_wind_direct[i],
                                                                                                  wind_level=
                                                                                                  miss_wind_level[i],
                                                                                                  aqi=miss_aqi[i])
            cur.execute(insert_str)
            conn.commit()
    else:
        for i in range(len(miss_time)):
            insert_str = "INSERT INTO weather_collect VALUES ('{date_str}','{city}','{time}','{tem}','{humidity}'," \
                         "'{rain}','{wind_angle}','{wind_direct}','{wind_level}','{aqi}')".format(date_str=dst[0],
                                                                                                  city=dst[1],
                                                                                                  time=miss_time[i],
                                                                                                  tem=miss_tem[i],
                                                                                                  humidity=
                                                                                                  miss_humidity[i],
                                                                                                  rain=miss_rain[i],
                                                                                                  wind_angle=
                                                                                                  miss_wind_angle[i],
                                                                                                  wind_direct=
                                                                                                  miss_wind_direct[i],
                                                                                                  wind_level=
                                                                                                  miss_wind_level[i],
                                                                                                  aqi=miss_aqi[i])
            cur.execute(insert_str)
            conn.commit()
    conn.close()
    return None


def main(http, city, code):
    # 抓取7天内天气网页
    web = '/'.join([http, 'weather', code]) + '.shtml'
    html = geturl(web)
    if html == None:
        raise Exception("抓取网页失败")

    observe_var = re.findall(r'observe24h_data = .*;', html)[0]
    observe_str = observe_var[:-1].replace(' ', '').split('=')[1]
    observe_json = json.loads(observe_str)
    observe_data = observe_json['od']['od2']
    # 清洗数据
    dtime = []
    tem = []
    humidity = []
    rain = []
    wind_angle = []
    wind_direct = []
    wind_level = []
    aqi = []
    for idata in observe_data[::-1]:
        dtime.append(int(idata['od21']))
        tem.append(int(idata['od22']))
        wind_angle.append(int(idata['od23']))
        wind_direct.append(idata['od24'])
        wind_level.append(int(idata['od25']))
        rain.append(float(idata['od26']))
        humidity.append(int(idata['od27']))
        if idata['od28'] == '':
            aqi.append(0)
        else:
            aqi.append(int(idata['od28']))
    if dtime.count(0) == 2:
        split_point = 24
    else:
        split_point = dtime.index(0)
    # 保存天气信息
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    today_tuple = (date, city_name[city])
    date = (datetime.datetime.now() + datetime.timedelta(days=-1)).strftime("%Y-%m-%d")
    yesterday_tuple = (date, city_name[city])
    # 连接数据库
    conn = psycopg2.connect(database="weather_test", user="sa", password="Nydsj@222", host="192.168.0.250", port="5432")
    cur = conn.cursor()
    # 选择数据
    select_str = "SELECT * FROM weather_collect WHERE date1='{date}' AND city='{city}'".format(date=today_tuple[0],
                                                                                               city=today_tuple[1])
    cur.execute(select_str)
    content = cur.fetchall()
    conn.close()
    if len(content) == 0:
        # 保存昨天信息
        start_point = 0
        end_point = split_point
        save_file(start_point, end_point, yesterday_tuple, dtime, tem, humidity, rain, wind_angle, wind_direct,
                  wind_level, aqi)
    # 保存今天信息
    start_point = split_point
    end_point = 25
    # 规避网站更新时间延迟错误
    craw_time = int(datetime.datetime.now().strftime("%H"))
    # 获取爬取的时间中最后的时间
    last_h = dtime[start_point: end_point][-1]
    if last_h <= craw_time:
        save_file(start_point, end_point, today_tuple, dtime, tem, humidity, rain, wind_angle, wind_direct,
                  wind_level,
                  aqi)
    return None


if __name__ == '__main__':
    # 待抓取地区的网址
    https = "http://www.weather.com.cn"
    for icity, icode in city_dict.items():
        main(https, icity, icode)
