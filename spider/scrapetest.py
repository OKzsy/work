#!/usr/bin/env python
# -*- coding:utf-8 -*-


from urllib.request import urlopen, Request, URLError, HTTPError
from bs4 import BeautifulSoup

# url = "http://pythonscraping.com/pages/page1.html"
# url = "http://www.pythonscraping.com/pages/warandpeace.html"
url = "http://www.pythonscraping.com/pages/page3.html"
html = urlopen(url)
bsObj = BeautifulSoup(html.read(), features="lxml")
# for child in bsObj.find("table", id="giftList").children:
# #     print(child)

print(bsObj.find("", {"src": "../img/gifts/img1.jpg"}).parent.previous_sibling.get_text())
