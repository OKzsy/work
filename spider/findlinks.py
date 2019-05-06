#!/usr/bin/env python
# -*- coding:utf-8 -*-


from urllib.request import urlopen
from bs4 import BeautifulSoup
import re
import datetime
import random

pages = set()
random.seed(datetime.datetime.now())


def getInternalLinks(data, includeUrl):
    inLinks = []

    for link in data.findAll("a", href=re.compile("^(/|.*" + includeUrl + ")")):
        if link.attrs['href'] is not None:
            if link.attrs['href'] not in inLinks:
                inLinks.append(link.attrs['href'])

    return inLinks


def getExLinks(data, excludeUrl):
    exLinks = []

    for link in data.findAll("a", href=re.compile("^(https*|www)((?!" + excludeUrl + ").)*$")):
        if link.attrs['href'] is not None:
            if link.attrs['href'] not in exLinks:
                exLinks.append(link.attrs['href'])

    return exLinks


def splitAddress(address):
    begin_str = re.compile("^(http).*://").match(address).group(0)
    addressParts = address.replace(begin_str, "").split("/")

    return addressParts


def getRandomExtLink(startPage):
    html = urlopen(startPage)
    data = BeautifulSoup(html, "html.parser")
    exLinks = getExLinks(data, splitAddress(startPage)[0])

    if len(exLinks) == 0:
        inLinks = getInternalLinks(data, splitAddress(startPage)[0])
        return getRandomExtLink(inLinks[random.randint(0, len(inLinks) - 1)])
    else:
        return exLinks[random.randint(0, len(exLinks) - 1)]


def followExtOnly(startSite):
    extLink = getRandomExtLink(startSite)
    print("extLink:" + extLink)
    followExtOnly(extLink)


followExtOnly("https://makerfaire.com/")
