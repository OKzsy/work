#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2021/5/19 9:09
# @Author  : zhaoss
# @FileName: weather_nmc_postsql.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
从中国气象台获取未来6天的天气预报，并将数据写入数据库

Parameters


"""

import os
from selenium import webdriver
import psycopg2
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import datetime
from bs4 import BeautifulSoup

# from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

# desired_capabilities = DesiredCapabilities.CHROME
# desired_capabilities["pageLoadStrategy"] = "none"
city_dict = {
    'changyuan': '长垣',
    'zhengzhou': '郑州',
    'qixian': '淇县',
    'yongcheng': '永城',
    'xinye': '新野',
}


def get_web(drv, province, name):
    element = drv.find_element(by=By.XPATH, value="//select[@id='provinceSel']")
    all_options = element.find_elements(by=By.TAG_NAME, value="option")
    for option in all_options:
        if option.text == province:
            option.click()
            break
    element = drv.find_element(by=By.XPATH, value="//select[@id='citySel']")
    all_options = element.find_elements(by=By.TAG_NAME, value="option")
    for option in all_options:
        if option.text == name:
            option.click()
            break
    return drv.page_source


def main(http, province='河南省'):
    # 抓取未来天气预报详情
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('log-level=3')
    chrome_options.add_argument(r'--user-data-dir=C:\Users\01\AppData\Local\Google\Chrome\User Data\Default')
    # 开启静默模式
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(http)
    driver.find_element(by=By.CSS_SELECTOR, value='#indexMyWeather > div.hp.hp2.hp3 > div > div > div.seven-day-forecast').click()
    # 连接数据库
    conn = psycopg2.connect(database="WebGis", user="sa", password="Nydsj@222", host="192.168.0.250", port="5432")
    cur = conn.cursor()
    # 分城市抓取
    for city_name in list(city_dict.keys()):
        source = get_web(driver, province, city_dict[city_name])
        # 解析网页
        bsobj = BeautifulSoup(source, features="lxml")
        # 创建输出文件
        date = datetime.datetime.now().strftime("%Y-%m-%d")
        day = datetime.datetime.now()
        title = ','.join(
            ['city', 'get_day', 'day', 'time', 'rain', 'tem', 'wind_speed', 'wind_direct', 'press', 'humidity'])
        # 获取数据
        forcast_tags = bsobj.find_all('div', {"class": "clearfix pull-left"})
        count = 0
        for tag in forcast_tags:
            s = tag.text.replace('-', '0.0mm').split()
            for idx in range(0, len(s), 8):
                sub_s = s[idx: idx + 8]
                hour = sub_s[0].split('日')
                if len(hour) == 2:
                    count += 1
                tmp_day = (day + datetime.timedelta(days=count)).strftime("%Y-%m-%d")
                if count == 7:
                    break
                rain = sub_s[1][:-2]
                tem = sub_s[2][:-1]
                if '0.0mm' in tem:
                    tem = tem.replace('0.0mm', '-')
                wind_speed = sub_s[3][:-3]
                press = sub_s[5][:-3]
                humidity = sub_s[6][:-1]
                out_message = ','.join([repr(k) for k in
                                        [city_dict[city_name], date, tmp_day, hour[-1], rain, tem, wind_speed, sub_s[4], press,
                                         humidity]])
                insert_str = "INSERT INTO weather_forecast_detail ({}) VALUES ({})".format(title, out_message)
                cur.execute(insert_str)
                conn.commit()
    conn.close()
    driver.quit()
    return None


if __name__ == '__main__':
    # 待抓取地区的网址
    https = "http://www.nmc.cn/publish/forecast"
    main(https)
