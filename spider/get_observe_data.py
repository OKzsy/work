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
    'zhengzhou': '101180101',
    'yongcheng': '101181009',
    'xinye': '101180709',
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
    # 获取文件内容检查并更新
    if os.path.exists(dst):
        fj = open(dst, 'r')
        lines = fj.readlines()
        fj.close()
        content = []
        lines_num = 0
        for line in lines:
            content.append(line.strip().split())
            lines_num += 1
        last_line = content[-1]
        last_time = int(last_line[0])
        check_point = miss_time.index(last_time)
        content[-1][-1] = miss_aqi[check_point]
        # 增加判断，修改服务器丢失数据的问题
        for i in range(lines_num):
            tmp_time = int(content[i][0])
            error_flag = content[i][1]
            if (error_flag == '-999') and (tmp_time in miss_time):
                fi = miss_time.index(tmp_time)
                content[i] = [miss_time[fi], miss_tem[fi], miss_humidity[fi], miss_rain[fi], miss_wind_angle[fi], miss_wind_direct[fi],
                              miss_wind_level[fi], miss_aqi[fi]]
        for i in range(check_point + 1, len(miss_time)):
            tmp = [miss_time[i], miss_tem[i], miss_humidity[i], miss_rain[i], miss_wind_angle[i], miss_wind_direct[i],
                   miss_wind_level[i], miss_aqi[i]]
            content.append(tmp)
        fj = open(dst, 'w', newline='')
        for line in content:
            tmp = ['{:<7}'.format(str(val)) for val in line]
            fj.writelines(tmp)
            fj.write('\r\n')
        tmp = None
        fj.close()
    else:
        fj = open(dst, 'w', newline='')
        for i in range(len(miss_time)):
            tmp = ['{:<7}'.format(str(val)) for val in [miss_time[i],
                                                        miss_tem[i],
                                                        miss_humidity[i],
                                                        miss_rain[i],
                                                        miss_wind_angle[i],
                                                        miss_wind_direct[i],
                                                        miss_wind_level[i],
                                                        miss_aqi[i]]]
            fj.writelines(tmp)
            fj.write('\r\n')
        tmp = None
        fj.close()
    return None


def main(http, city, code, dst):
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
        tem.append(float(idata['od22'] if idata['od22'] != '' else -999))
        wind_angle.append(int(idata['od23'] if idata['od23'] != '' else -999))
        wind_direct.append(idata['od24'] if idata['od24'] != '' else -999)
        wind_level.append(int(idata['od25'] if idata['od25'] != '' else -999))
        rain.append(float(idata['od26'] if idata['od26'] != '' else -999))
        humidity.append(int(idata['od27'] if idata['od27'] != '' else -999))
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
    dir_path = os.path.join(dst, city)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    today_dst_file = os.path.join(dir_path, city) + '-' + date + '.txt'
    date = (datetime.datetime.now() +
            datetime.timedelta(days=-1)).strftime("%Y-%m-%d")
    yesterday_dst_file = os.path.join(dir_path, city) + '-' + date + '.txt'
    if not os.path.exists(today_dst_file):
        # 保存昨天信息
        start_point = 0
        end_point = split_point
        save_file(start_point, end_point, yesterday_dst_file, dtime, tem, humidity, rain, wind_angle, wind_direct,
                  wind_level, aqi)
    # 保存今天信息
    start_point = split_point
    end_point = 25
    # 规避网站更新时间延迟错误
    craw_time = int(datetime.datetime.now().strftime("%H"))
    # 获取爬取的时间中最后的时间
    last_h = dtime[start_point: end_point][-1]
    if last_h <= craw_time:
        save_file(start_point, end_point, today_dst_file, dtime, tem, humidity, rain, wind_angle, wind_direct, wind_level,
                  aqi)
    return None


if __name__ == '__main__':
    # 待抓取地区的网址
    https = "http://www.weather.com.cn"
    dst_dir = r"F:\testdata\weather_test"
    for icity, icode in city_dict.items():
        main(https, icity, icode, dst_dir)
