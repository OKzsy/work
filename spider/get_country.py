#!/usr/bin/env python
# -*- coding:utf-8 -*-


from urllib.request import urlopen, HTTPError
from bs4 import BeautifulSoup
import re
import json
import datetime
import random


def getLinks(articalUrl):
    html = urlopen("https://en.wikipedia.org" + articalUrl)
    bsObj = BeautifulSoup(html, features="lxml")

    return bsObj.find("div", {"id": "bodyContent"}).findAll("a",
                                                            href=re.compile("^(/wiki/)((?!:).)*$"))


def getHistoryIPs(pageUrl):
    # 编辑历史页面URL
    pageUrl = pageUrl.replace('/wiki/', '')
    historyurl = "https://en.wikipedia.org/w/index.php?title=" + \
                 pageUrl + "&action=history"
    # print("histoyt url is {}".format(historyurl))
    html = urlopen(historyurl)
    bsObj = BeautifulSoup(html, features="lxml")
    # 找出class属性是"mw-anonuserlink"的链接
    # 它们用IP地址代替用户名
    ipAddresses = bsObj.findAll("a", {"class": "mw-userlink mw-anonuserlink"})
    addressList = set()
    for ipAddress in ipAddresses:
        addressList.add(ipAddress.get_text())
    return addressList


def getCountry(ipAddress):
    try:
        response = urlopen("http://api.ipstack.com/" + ipAddress +
                           "?access_key=be4a6a481869c5a6a44aea9e81752e5c").read().decode('utf-8')
    except HTTPError:
        return None
    responseJson = json.loads(response)
    return responseJson.get("country_name")


links = getLinks("/wiki/Python_(programming_language)")

while (len(links) > 0):
    for link in links:
        print('-------------------')
        historyIPs = getHistoryIPs(link.attrs['href'])
        for historyIP in historyIPs:
            # print("IP地址为: {}".format(historyIP))
            country = getCountry(historyIP)
            if country is not None:
                print("{} is from {}".format(historyIP, country))
    # 跳转新网页
    newLink = links[random.randint(0, len(links) - 1)].attrs["href"]
    links = getLinks(newLink)
print('end')
