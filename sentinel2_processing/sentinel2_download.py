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
import xml.etree.ElementTree as ET
from requests.auth import HTTPBasicAuth, AuthBase

headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Host": "scihub.copernicus.eu",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "Windows",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
}


def BuildOptions(platformname='Sentinel-2',
                 tile='50SKE',
                 begintime=None,
                 endtime=None,
                 filename=None,
                 footprint=None,
                 producttype='S2MSI1C',
                 cloud=100,
                 page_size=50,
                 page_start_value=0):
    options = []
    # 页面配置
    if page_start_value is not None:
        options += ['start=' + str(page_start_value)]
    if page_size is not None:
        options += ['rows=' + str(page_size)]
    # 查询关键字
    query = []
    if tile is not None:
        query += [tile]
    if footprint is not None:
        # 有待完善
        query += ['filename:' + filename]
    query1 = []
    if begintime is None:
        begintime = 'NOW-6MONTHS TO '
    else:
        begintime = begintime + 'T00:00:00.000Z TO '
    if endtime is None:
        endtime = 'NOW'
    else:
        endtime = endtime + 'T23:59:59.999Z'
    query1 += ['beginPosition:' + '[' + begintime + endtime + ']']
    query1 += ['endPosition:' + '[' + begintime + endtime + ']']
    query1_combine = ' AND '.join(query1)
    query += ['(' + query1_combine + ')']
    query2 = []
    if platformname is not None:
        query2 += ['platformname:' + platformname]
    if producttype is not None:
        query2 += ['producttype:' + producttype]
    if filename is not None:
        query2 += ['filename:' + filename]
    if cloud is not None:
        query2 += ['cloudcoverpercentage:' +
                   '[' + '0' + ' TO ' + str(cloud) + ']']
    query2_combine = ' AND '.join(query2)
    query += ['(' + query2_combine + ')']
    query_combine = 'q=' + ' AND '.join(query)
    options += [query_combine]
    options_combine = '&'.join(options)
    return options_combine


def parse_xml(root, flag, attri=None, attri_value=None, namespace=None):
    # 判断获取的数据内容
    flag_name = flag.split(':')[1]
    # 匹配节点
    content = []
    if flag_name == 'entry':
        file_name = []
        data_link = []
        quicklook_link = []
        for node in root.findall(flag, namespace):
            # 获取文件名
            file_name.append(node.find('root:title', namespace).text)
            # 获取数据链接
            for link in node.findall('root:link', namespace):
                attrib_lst = link.items()
                attrib_num = len(attrib_lst)
                if attrib_num == 1:
                    data_link.append(attrib_lst[0][1])
                elif attrib_lst[0][1] == 'icon':
                    quicklook_link.append(attrib_lst[1][1])
        return file_name, data_link, quicklook_link
    else:
        for node in root.findall(flag, namespace):
            if attri:
                if node.attrib[attri] == attri_value:
                    pass
            else:
                content.append(node.text)
                pass
    return content


def download(url, dst):
    # 创建会话，获取文件大小
    html = requests.get(url, headers=headers, stream=True, auth=HTTPBasicAuth(
        username='hpu_zss', password='120503xz'))
    print(html.status_code)
    # 文件总大小
    total_size = int(html.headers['content-length'])
    # 获取目标文件是否存在，存在则获取大小
    if os.path.exists(dst):
        temp_size = os.path.getsize(dst)
    else:
        temp_size = 0
    if total_size == temp_size:
        return None
    else:
        # 下载数据
        header = {'Range': 'bytes={0}-'.format(str(temp_size))}
        html = requests.get(url, headers=header, stream=True, auth=HTTPBasicAuth(
        username='hpu_zss', password='120503xz'))
        with open(dst, 'ab') as f:
            f.write(html.content)
        time.sleep(2)
    return None


def main():
    # 创建查询条件
    res = BuildOptions()
    # 查询数据
    base_url = 'https://scihub.copernicus.eu/dhus/search?'
    url = base_url + res
    html = requests.get(url, headers=headers, auth=HTTPBasicAuth(
        username='hpu_zss', password='120503xz'))
    # 获取数据列表
    xmlroot = ET.fromstring(html.text)
    # 去除命名空间的影响
    ns = {"opensearch": "http://a9.com/-/spec/opensearch/1.1/",
          "root": "http://www.w3.org/2005/Atom"}
    # 获取数据个数
    total_imgs = parse_xml(xmlroot, 'opensearch:totalResults', namespace=ns)
    # 获取数据名称,数据链接,快视图链接
    file_names, data_links, quickview_links = parse_xml(
        xmlroot, 'root:entry', namespace=ns)
    # 下载数据
    # for i in range(len(file_names)):
    #     name = file_names[i]
    #     url = quickview_links[i]
    #     dst = os.path.join(r'F:\test\S2', name) + '.jpg'
    #     download(url, dst)
    # html = requests.get(url, headers=headers, stream=True, auth=HTTPBasicAuth(
    #     username='hpu_zss', password='120503xz'))
    name = file_names[0]
    url = quickview_links[0]
    dst = os.path.join(r'F:\test\S2', name) + '.jpg'
    download(url, dst)
    return None


if __name__ == '__main__':
    # 待抓取地区的网址
    main()
