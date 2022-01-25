#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2022/1/25 17:08
# @Author  : zhaoss
# @FileName: update_chromedriver.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import re
import shutil
import winreg
import zipfile
import requests

base_url = 'http://npm.taobao.org/mirrors/chromedriver/'
version_re = re.compile(r'^[1-9]\d*\.\d*.\d*')  # 匹配前3位版本号的正则表达式


def getChromeVersion():
    """通过注册表查询chrome版本"""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Software\\Google\\Chrome\\BLBeacon')
        value, t = winreg.QueryValueEx(key, 'version')
        return version_re.findall(value)[0]  # 返回前3位版本号
    except WindowsError as e:
        # 没有安装chrome浏览器
        return "1.1.1"


def getChromeDriverVersion():
    """查询Chromedriver版本"""
    outstd2 = os.popen('chromedriver --version').read()
    try:
        version = outstd2.split(' ')[1]
        version = ".".join(version.split(".")[:-1])
        return version
    except Exception as e:
        return "0.0.0"


def getLatestChromeDriver(version):
    # 获取该chrome版本的最新driver版本号
    url = f"{base_url}LATEST_RELEASE_{version}"
    latest_version = requests.get(url).text
    # 下载chromedriver
    download_url = f"{base_url}{latest_version}/chromedriver_win32.zip"
    file = requests.get(download_url)
    with open("chromedriver.zip", 'wb') as zip_file:  # 保存文件到脚本所在目录
        zip_file.write(file.content)
    # 解压
    f = zipfile.ZipFile("chromedriver.zip", 'r')
    for file in f.namelist():
        f.extract(file)
    shutil.move("chromedriver.exe", r"D:\browserDriver\chromedriver.exe")
    os.remove("chromedriver.zip")


def main():
    chrome_version = getChromeVersion()
    driver_version = getChromeDriverVersion()
    if chrome_version == driver_version:
        pass
        return
    try:
        getLatestChromeDriver(chrome_version)
    except requests.exceptions.Timeout:
        pass
    except Exception as e:
        pass


if __name__ == "__main__":
    main()
