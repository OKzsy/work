#!/usr/bin/env python
# _*_ coding:utf-8 _*_
#
# @Version : 1.0
# @Time    : 2020/04/15
# @Author  : zhaoss
# @File    : get_H8
# @Description: http://himawari8.nict.go.jp/ 向日葵8号卫星实时图片下载
#
#
from PIL import Image
import requests
import re
import os
import datetime


def download_img(url, img_save_path):
    header = {
        'Referer': 'https://himawari.asia/',
        'Sec-Fetch-Dest': 'image',
        'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36(KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36'
    }
    img = requests.get(url, headers=header)
    with open(img_save_path, "wb") as fwi:
        fwi.write(img.content)
        print(img_save_path + "图片下载成功")


def fill_img(img, img_save_path):
    width, height = 1920, 1080      # 电脑屏幕大小
    new_img = Image.new(img.mode, (width, height), color='black')
    new_img.paste(img, (int(width/2 - 250), int(height/2 - 250)))
    new_img.save(img_save_path)
    print(img_save_path + "图片合成成功")


def dl_main():
    # 获取当前系统时间
    utc_today = datetime.datetime.utcnow() - datetime.timedelta(minutes=70)  # 获取GMT时间并减去70分钟
    delat_utc_today = utc_today.strftime("%Y/%m/%d/%H%M")  # 时间格式化
    # 分钟向下取整
    delat_utc_today_list = list(delat_utc_today)
    delat_utc_today_list[-1] = "0"
    delat_utc_today = "".join(delat_utc_today_list)
    # 整合为链接 格式为：http://himawari8-dl.nict.go.jp/himawari8/img/D531106/1d/550/2018/09/25/065000_0_0.png
    img_url = "https://himawari8-dl.nict.go.jp/himawari.asia/img/D531106/thumbnail/550/" + delat_utc_today + "00_0_0.png"
    name = delat_utc_today.replace("/", "_") + "00_0_0.png"  # 获取图片名字
    # 图片保存路径
    new_name = 'new_' + name
    img_save_path = "D:\\back_pic\\" + name
    new_img_save_path = "D:\\back_pic\\" + new_name
    # 下载图片
    download_img(img_url, img_save_path)
    # 合成图片
    img = Image.open(img_save_path)
    fill_img(img, new_img_save_path)
    os.remove(img_save_path)
    return new_name


if __name__ == '__main__':
    dl_main()
