#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2021/2/21 12:51
# @Author  : zhaoss
# @FileName: get_real_temperture.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
每隔一个小时从中国天气网中爬取指定地区百叶箱真实的温度，相对湿度和降雨量

Parameters
http://www.weather.com.cn/weather/101180308.shtml

"""
import os
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from datetime import datetime
from bs4 import BeautifulSoup


def parse_paramet(drv):
    # 获取表格的高度
    height = drv.find_element_by_css_selector('#hourHolder > svg > rect:nth-child(4)').get_attribute('height')
    # 获取对应的温度范围yLabel
    tem_range = []
    for itag in drv.find_elements_by_css_selector('#hourHolder > div.yLabel > span'):
        tem_range.append(itag.text)
    # 获取对应的时间
    time_range = []
    for itag in drv.find_elements_by_css_selector('#hourHolder > div.xLabel > span'):
        time_range.append(itag.text)
    # 获取真实温度对应的高度
    real_tem_height = []
    for itag in drv.find_elements_by_css_selector('#hourHolder > svg > circle'):
        real_tem_height.append(itag.get_attribute('cy'))
    return time_range, tem_range, height, real_tem_height


def calculate_real_paramet(xr, yr, yrect, parament):
    xrange = [int(val) for val in xr]
    yrange = [int(val) for val in yr]
    yrect = int(yrect)
    para = [float(val) for val in parament]
    # 计算yrange的差值
    diff_y = yrange[0] - yrange[-1]
    real_paras = []
    for ival in range(len(para)):
        real_para = (yrect - para[ival]) * diff_y / yrect + yrange[-1]
        real_paras.append(round(real_para, 1))
    return xrange, real_paras


def main(http, code, dst):
    # 抓取实况天气
    web = '/'.join([http, 'weather', code]) + '.shtml'
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('log-level=3')
    # 开启静默模式
    driver = webdriver.Chrome(chrome_options=chrome_options)
    # driver = webdriver.Chrome()
    driver.get(web)
    # 获取温度
    xlabel, ylabel, height, paraments = parse_paramet(driver)
    # 计算真实参数
    time, tem = calculate_real_paramet(xlabel, ylabel, height, paraments)
    # 获取相对湿度
    contral_tag = driver.find_element_by_css_selector('#weatherChart > div.tabs > ul > li.sd')
    contral_tag.click()
    xlabel, ylabel, height, paraments = parse_paramet(driver)
    # 计算真实参数
    time, humidity = calculate_real_paramet(xlabel, ylabel, height, paraments)
    humidity = [val + 2 for val in humidity]
    # 保存天气信息
    date = datetime.now().strftime("%Y-%m-%d")
    dst_file = os.path.join(dst, date) + '.txt'
    start_time = 23
    if os.path.exists(dst_file):
        fj = open(dst_file, 'r+', newline='')
        # 获取文件最后一行以获取最后更新时间
        lines = fj.readlines()
        last_line = lines[-1]
        line = last_line.rstrip().split(' ')
        start_time = int(line[0])
    else:
        fj = open(dst_file, 'a', newline='')
    start_point = time.index(start_time, 1)
    missing_time = time[start_point + 1:]
    missing_tem = tem[start_point + 1:]
    missing_humidity = humidity[start_point + 1:]
    for i in range(len(missing_time)):
        tmp = ['{:<5}'.format(str(val)) for val in [missing_time[i], missing_tem[i], missing_humidity[i]]]
        fj.writelines(tmp)
        fj.write('\r\n')
    fj.close()
    driver.quit()
    return None


if __name__ == '__main__':
    # 待抓取地区的网址
    https = "http://www.weather.com.cn"
    cite_code = "101180308"
    dst_dir = r"F:\test"
    main(https, cite_code, dst_dir)
