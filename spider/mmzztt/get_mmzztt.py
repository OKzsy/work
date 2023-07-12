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
import execjs
from typing import List
import binascii
import json

import requests
from lxml import etree
from Crypto.Cipher import AES
from Crypto.Hash import MD5

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

def decrypt(pid, cache_sign):
    pid = int(pid)
    IV = "".join([str(pid % i % 9) for i in range(2, 18)]).encode()
    key = MD5.new((f"{pid}{pid % 9}{pid % 8}").encode()).hexdigest()[8:24].encode('utf-8')
    aes = AES.new(key, AES.MODE_CBC, IV)
    result = aes.decrypt(binascii.a2b_hex(cache_sign)).rstrip()
    return json.loads(result.decode('utf-8'))

def main(http, dst, province='河南省'):
    # 抓取未来天气预报详情
    chrome_options = Options()
    # chrome_options.add_argument("--headless=new")
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('log-level=3')
    chrome_options.add_argument(
        r'--user-data-dir=C:\Users\01\AppData\Local\Google\Chrome\User Data\Default')
    # 开启静默模式
    # driver = webdriver.Chrome(options=chrome_options)
    # driver.get(http)
    # session_storage = driver.execute_script("return sessionStorage;")
    # sign = session_storage["cache_87789"]
    sign = 'c79a1b3b7166ad903c6f187b6db7255f97cba7c46dfa9b88b62caa6b621d92c43ed1a01f8' +\
    '899563808e6bdd7e6ae26cbc07e6f8cd878dbc2c1b0749f3ed7329d0c37c4dfe9aca310b351907798' +\
    '9b53d75c14648a3b32842d5261b53e4cf92b47b8ddc3fcc61d878cad05cab4334e9c9519fa2875df12' +\
    'caa931ea9d1224ccb9810da6aea5580f5bff6da0c2c5a4d216d1c560773cc5a36a98a74611c30edf70' +\
    '9b8bf318ad0729d9337dbccf3d6a5ff2835f1d763a9fb3bba7f6af2e5b41743ea2e4bf8a875ff92d92' +\
    'af145ce5dda177d4c0880fcc7d7946751b6e3388ffbe91b54fc79edb1750c4ea1c685db8b1351afd02' +\
    'd7c1fbf47c99d4bc7375e5ca1fb970f7c8cc11d2be5165dbb13d4d3328401b37d77e1b787d9071d79c' +\
    '874f6e5cb54e7497ad6a71fe574f38b3f0445d97ccc72123a4896cad785fbfd71951fdc31ebc06383b' +\
    'b276e8199fdcbee6f225e5c0e6054987b7a03955e02a156c9eecd5cc9cb08be64c730c8fa43a8165d6' +\
    '256f8fdd72a8e924c6bce553f6c94e9764c0cf86'
    # with open(r'spider\mmzztt\mzt.js', mode='r') as f:
    #     js_code = f.read()
    # js = execjs.compile(js_code)
    # data = js.call('address', "87789", sign)
    # print(session_storage)
    res = decrypt("87789", sign)
    print('end')
    # driver.find_element(by=By.CSS_SELECTOR,value='#indexMyWeather > div.hp.hp2.hp3 > div > div > div.seven-day-forecast').click()
    # # 分城市抓取
    # for city_name in list(city_dict.keys()):
    #     source = get_web(driver, province, city_dict[city_name])
    #     # 解析网页
    #     bsobj = BeautifulSoup(source, features="lxml")
    #     # 创建输出文件
    #     date = datetime.now().strftime("%Y-%m-%d")
    #     day = datetime.now().strftime("%d")
    #     dst_file = os.path.join(dst, city_name) + '-' + date + '_detail.txt'
    #     fj = open(dst_file, 'w', newline='')
    #     title = ','.join(
    #         ['day', 'time', 'rain(mm)', 'tem(°C)', 'wind_speed(m/s)', 'wind_direct', 'press(hPa)', 'humidity(%)'])
    #     fj.write(title)
    #     fj.write('\n')
    #     # 获取数据
    #     forcast_tags = bsobj.find_all('div', {"class": "clearfix pull-left"})
    #     count = 0
    #     for tag in forcast_tags:
    #         s = tag.text.replace('-', '0.0mm').split()
    #         for idx in range(0, len(s), 8):
    #             sub_s = s[idx: idx + 8]
    #             hour = sub_s[0].split('日')
    #             if len(hour) == 2:
    #                 day = hour[0]
    #                 count += 1
    #             tmp_day = day + '日'
    #             if count == 7:
    #                 break
    #             rain = sub_s[1][:-2]
    #             tem = sub_s[2][:-1]
    #             if '0.0mm' in tem:
    #                 tem = tem.replace('0.0mm', '-')
    #             wind_speed = sub_s[3][:-3]
    #             press = sub_s[5][:-3]
    #             humidity = sub_s[6][:-1]
    #             out_message = ','.join(
    #                 [tmp_day, hour[-1], rain, tem, wind_speed, sub_s[4], press, humidity])
    #             fj.write(out_message)
    #             fj.write('\n')
    #     fj.close()
    # driver.quit()
    return None


if __name__ == '__main__':
    # 待抓取地区的网址
    https = "https://mmzztt.com/photo/87789"
    dst_dir = r"F:\weather\changyuan\predict"
    main(https, dst_dir)
