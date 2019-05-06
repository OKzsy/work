#!/usr/bin/env python
# -*- coding:utf-8 -*-


from urllib.request import urlopen, Request, URLError, HTTPError
from bs4 import BeautifulSoup
import datetime
import random
import re

random.seed(datetime.datetime.now())
pages = set()


# def getLinks(articalUrl):
#     html = urlopen("https://en.wikipedia.org" + articalUrl)
#     bsObj = BeautifulSoup(html, features="lxml")
#
#     return bsObj.find("div", {"id": "bodyContent"}).findAll("a",
#                                                             href=re.compile("^(/wiki/)((?!:).)*$"))
def getLinks(articalUrl):
    global pages
    html = urlopen("https://en.wikipedia.org" + articalUrl)
    bsObj = BeautifulSoup(html, features="lxml")
    try:
        print(bsObj.h1.get_text())
        print(bsObj.find(id="mw-content-text").findAll("p")[0])
    except AttributeError:
        print("页面缺少一些属性！不过不用担心！")

    for link in bsObj.find("div", {"id": "bodyContent"}).findAll("a",
                                                                 href=re.compile("^(/wiki/)((?!:).)*$")):
        if 'href' in link.attrs:
            if link.attrs['href'] not in pages:
                newpage = link.attrs['href']
                print("我们找到了新的网页：{}".format(newpage))
                pages.add(newpage)
                getLinks(newpage)


links = getLinks("/wiki/Kevin_Bacon")
