# Python学习群548377875
import requests
from bs4 import BeautifulSoup
import os
import re
import numpy as np

Hostreferer = {
    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)',
    'Referer': 'http://www.mzitu.com'
}
Picreferer = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36',
    'Referer': 'https://www.mzitu.com'
}


def get_atlas_list(url):
    req = requests.get(url, headers=Hostreferer)
    soup = BeautifulSoup(req.text, 'lxml')
    atlas = soup.find_all(attrs={'class': 'lazy'})
    # atlas = soup.find_all(attrs={'title':'日本妹子'})
    atlas_list = []
    for atla in atlas:
        atlas_list.append(atla.attrs['data-original'])
    return atlas_list


def save_one_page(start_url):
    global num
    atlas_url = get_atlas_list(start_url)
    new_name = 'jiepai'
    if not os.path.exists(new_name):
        os.mkdir(new_name)
    for url in atlas_url:
        req = requests.get(url, headers=Picreferer)
        with open(new_name+'/'+str(num)+'.jpg', 'wb') as f:
            f.write(req.content)
        num += 1


if __name__ == '__main__':
    start_url = "http://www.mzitu.com/jiepai/"
    num = 1
    for count in np.random.randint(1, 20, 15):
        # url = start_url + "page/" + str(count) +"/" comment-page-2/#comments
        url = start_url + "comment-page-" + str(count) + "/#comments"
        save_one_page(url)
    print("爬取完成")
