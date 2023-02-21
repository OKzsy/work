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
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from datetime import datetime
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

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


def main(http, dst, province='河南省'):
    # 抓取未来天气预报详情
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('log-level=3')
    chrome_options.add_argument(
        r'--user-data-dir=C:\Users\01\AppData\Local\Google\Chrome\User Data\Default')
    # 开启静默模式
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(http)
    driver.find_element(by=By.CSS_SELECTOR,value='#indexMyWeather > div.hp.hp2.hp3 > div > div > div.seven-day-forecast').click()
    # 分城市抓取
    for city_name in list(city_dict.keys()):
        source = get_web(driver, province, city_dict[city_name])
        # 解析网页
        bsobj = BeautifulSoup(source, features="lxml")
        # 创建输出文件
        date = datetime.now().strftime("%Y-%m-%d")
        day = datetime.now().strftime("%d")
        dst_file = os.path.join(dst, city_name) + '-' + date + '_detail.txt'
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
    driver.quit()
    return None


if __name__ == '__main__':
    # 待抓取地区的网址
    https = "http://www.nmc.cn/publish/forecast"
    dst_dir = r"F:\weather\changyuan\predict"
    main(https, dst_dir)
