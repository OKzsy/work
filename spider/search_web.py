from urllib.request import urlopen
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import re
import datetime
import random

pages = set()
random.seed(datetime.datetime.now())


def getExternalLink(bs, excludeurl):
    externalLinks = []
    # 找出所有以“http”或“www”开头且不包含当前url的连接
    for link in bs.find_all('a', href=re.compile('^(http|https|www)((?!excludeurl).)*$')):
        if link.attrs['href'] is not None:
            if link.attrs['href'] not in externalLinks:
                externalLinks.append(link.attrs['href'])
    return externalLinks


def getInternalLinks(bs, includeurl):
    includeurl = '{}://{}'.format(urlparse(includeurl).scheme,
                                  urlparse(includeurl).netloc)
    internalLinks = []
    # 找出所有以“/”开头的连接
    for link in bs.find_all('a', href=re.compile('^(/|.*' + includeurl + ')')):
        if link.attrs['href'] is not None:
            if link.attrs['href'] not in internalLinks:
                if link.attrs['href'].startswith('/'):
                    internalLinks.append(includeurl + link.attrs['href'])
                else:
                    internalLinks.append(link.attrs['href'])
    return internalLinks


def getRandomExternalLink(startingpage):
    html = urlopen(startingpage).read()
    bs = BeautifulSoup(html, 'lxml')
    externalLinks = getExternalLink(bs, urlparse(startingpage).netloc)
    if len(externalLinks) == 0:
        print('No external links, looking around the site for one')
        domain = '{}://{}'.format(urlparse(startingpage).scheme,
                                  urlparse(startingpage).netloc)
        internalLinks = getInternalLinks(bs, domain)
        return getRandomExternalLink(internalLinks[random.randint(0, len(internalLinks) - 1)])
    else:
        return externalLinks[random.randint(0, len(externalLinks) - 1)]



def followExternalOnly(startingSite):
    externalLink = getRandomExternalLink(startingSite)
    print("Random external link is {}".format(externalLink))
    followExternalOnly(externalLink)
    pass


def main(origin_url):
    followExternalOnly(origin_url)

    return None


if __name__ == "__main__":
    url = "https://malagis.com/"
    main(url)
    pass
