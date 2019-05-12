#!/usr/bin/env python3
# -*- coding:utf-8 -*-

# from urllib.request import urlopen, Request, URLError
from bs4 import BeautifulSoup
import numpy as np
import datetime
import os
import re
import requests

# 创建随机数种子
np.random.seed(datetime.datetime.now().microsecond)

Hostreferer = {
    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)',
    'Referer': 'http://www.mzitu.com'
}
Picreferer = {
    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)',
    'Referer': 'http://i.meizitu.net'
}


def get_tag(url):
    html = requests.get(url).text
    bsObj = BeautifulSoup(html, features="lxml")
    tags = bsObj.find('dl', attrs={"class": "tags"}).findAll("dd")
    tag_links = []
    tag_names = []
    for one_tag in tags:
        if 'href' in one_tag.a.attrs:
            tag_links.append(one_tag.a.attrs['href'])
            tag_names.append(one_tag.img.attrs['alt'])
    return tag_links, tag_names


def get_album(topic_link):
    # 获取指定连接内的所有相册名和连接
    alb_links = []
    alb_names = []
    html = requests.get(topic_link).text
    bsObj = BeautifulSoup(html, features="lxml")
    alb_tags = bsObj.findAll('img', {"class": "lazy"})
    for alb in alb_tags:
        if 'alt' in alb.attrs:
            alb_names.append(alb.attrs['alt'])
            alb_links.append(alb.parent.attrs['href'])
    return alb_links, alb_names


def get_pic_url(alb_url):
    # 获取相册中某一页中照片的url
    # alb_url = "https://www.mzitu.com/127079/15"
    html = requests.get(alb_url).text
    bsObj = BeautifulSoup(html, features="lxml")
    img_url = bsObj.find('div', {"class": "main-image"}).find("img").attrs['src']
    return img_url


def save_img(img_url, count, name):
    req = requests.get(img_url, headers=Picreferer)
    with open(name + '/' + str(count) + '.jpg', 'wb') as f:
        f.write(req.content)


def rename(name):
    # 使用正则表达式，规范文件名
    rstr = r'[\/\\\:\*\?\<\>\|]'
    new_name = re.sub(rstr, "", name)
    return new_name


def save_pic(link, name, pic_dir):
    name = rename(name)
    # 确定下载文件夹
    alb_dir = os.path.join(pic_dir, name)
    if not os.path.exists(alb_dir):
        os.mkdir(alb_dir)
    # html = urlopen(link)
    html = requests.get(link, headers=Hostreferer).text
    bsObj = BeautifulSoup(html, features="lxml")
    # 获取页面总数
    # page_num = bsObj.find('span', {"class": "dots"}).next_sibling.get_text()
    page_num = bsObj.find('span', text=re.compile("^(下一页).*")).parent.previous_sibling.span.get_text()
    print("图集--" + name + "--开始保存")
    for ipic in range(1, int(page_num) + 1):
        ialb_url = link + "/" + str(ipic)
        pic_url = get_pic_url(ialb_url)
        save_img(pic_url, ipic, alb_dir)
        print('正在保存第' + str(ipic) + '张图片')
    print("图集--" + name + "保存成功")
    return 1


def main(url):
    global pic_dir
    # 获取网页上所有的一级标签
    links, names = get_tag(url)
    for itopic in np.random.randint(0, len(links) - 1, 10):
        # 随机获取某一个专题，共获取10个专题
        print("Now begin to get the {} topic, whose link is: {}".format(names[itopic], links[itopic]))
        # 创建该主题的文件夹
        topic_dir = os.path.join(pic_dir, names[itopic])
        if not os.path.exists(topic_dir):
            os.mkdir(topic_dir)
        # 开始抓取主题内的图片
        # 获取该主题内所有的相册名及相册连接
        album_links, album_names = get_album(links[itopic])
        for ialb in np.random.randint(0, len(album_links) - 1, 3):
            # 随机获取某一个相册，共获取3个相册
            print("Now begin to get the {} album, whose link is: {}".format(album_names[ialb], album_links[ialb]))
            # 现在开始下载图片
            res = save_pic(album_links[ialb], album_names[ialb], topic_dir)
            pass
        pass

    pass


if __name__ == "__main__":
    # 图片存放路径
    pic_dir = r"E:\PythonCode\pic"
    # 通过标签下载图片
    source_url = "https://www.mzitu.com/zhuanti/"
    main(source_url)
    pass
