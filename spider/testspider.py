# #!/usr/bin/env python3
# # -*- coding:utf-8 -*-
# """
# # @Time    : 2019/3/27 14:23
# # @Author  : zhaoss
# # @FileName: testspider.py
# # @Email   : zhaoshaoshuai@hnnydsj.com
# Description:
#
#
# Parameters
#
#
# """
#
import os
import glob
import json
import requests
from bs4 import BeautifulSoup
import time
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


#
#
# def main(url):
#     headers = {
#         # 'Referer': 'http://www.santostang.com/2018/07/15/4-3-%e9%80%9a%e8%bf%87selenium-%e6%a8%a1%e6%8b%9f%e6%b5%8f%e8%a7%88%e5%99%a8%e6%8a%93%e5%8f%96/',
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'
#     }
#     response = requests.get(url, headers=headers, timeout=20)
#     # print("文本编码：", response.encoding)
#     json_string = response.text
#     json_string = json_string[json_string.find('{'): json_string.rfind('}') + 1]
#     json_data = json.loads(json_string)
#     comment_list = json_data['results']['parents']
#     for each in comment_list:
#         message = each['content']
#         print(message)
#     # print("响应状态：", response.status_code)
#     # print("字符串响应方式：", response.text)
#     # soup = BeautifulSoup(response.text, 'lxml')
#     # title = soup.find("h1", class_="post-title")
#     # print(title)
#
#     return None
#
#
# if __name__ == '__main__':
#     start_time = time.clock()
#     links = "https://api-zero.livere.com/v1/comments/list?callback=jQuery1124016430832975649268_1553740501274&limit=10&" + \
#             "repSeq=4272904&requestPath=%2Fv1%2Fcomments%2Flist&consumerSeq=1020&livereSeq=28583&smartloginSeq=5154&_=1553740501276"
#     main(links)
#     end_time = time.clock()
#
#     print("time: %.4f secs." % (end_time - start_time))

def single_page_comment(link):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}
    r = requests.get(link, headers=headers)
    # 获取 json 的 string
    json_string = r.text
    json_string = json_string[json_string.find('{'):-2]
    json_data = json.loads(json_string)
    comment_list = json_data['results']['parents']
    for eachone in comment_list:
        message = eachone['content']
        print(message)


def main():
    for page in range(1, 4):
        link1 = "https://api-zero.livere.com/v1/comments/list?callback=jQuery1124016430832975649268_1553740501274&limit=10&offset="
        link2 = "&repSeq=4272904&requestPath=%2Fv1%2Fcomments%2Flist&consumerSeq=1020&livereSeq=28583&smartloginSeq=5154&_=1553740501276"
        page_str = str(page)
        link = link1 + page_str + link2
        print(link)
        single_page_comment(link)


if __name__ == '__main__':
    start_time = time.clock()
    main()
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
