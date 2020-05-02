import requests
import json
import re

url = "https://c.y.qq.com/base/fcgi-bin/fcg_global_comment_h5.fcg"

querystring = {"g_tk": "5381", "loginUin": "0", "hostUin": "0", "format": "json", "inCharset": "utf8",
               "outCharset": "GB2312", "notice": "0", "platform": "yqq.json", "needNewCode": "0", "cid": "205360772",
               "reqtype": "2", "biztype": "1", "topid": "237773700", "cmd": "8", "needmusiccrit": "0", "pagenum": "0",
               "pagesize": "25", "lasthotcommentid": "", "domain": "qq.com", "ct": "24", "cv": "10101010"}

headers = {
    'Accept': "application/json, text/javascript, */*; q=0.01",
    'Referer': "https://y.qq.com/n/yqq/song/001qvvgF38HVc4.html",
    'Origin': "https://y.qq.com",
    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36",
    'Sec-Fetch-Mode': "cors",
    'Cache-Control': "no-cache",
    'Postman-Token': "09d9f473-9032-42ab-86eb-aa664f602f03,b2f42df5-9e43-42c1-97d6-777244a9d282",
    'Host': "c.y.qq.com",
    'Accept-Encoding': "gzip, deflate",
    'Connection': "keep-alive",
    'cache-control': "no-cache"
}

txt = r"F:\test_data\jax.txt"
file = open(txt, 'a', encoding='utf-8')
for i in range(2572):
    querystring['pagenum'] = str(i)
    response = requests.request("GET", url, headers=headers, params=querystring)
    comment_json = json.loads(response.text)
    comment_list = comment_json['comment']['commentlist']
    for comment in comment_list:
        rootcommentcontent = comment['rootcommentcontent']
        repil = re.compile(r'/[em].*[/em].', re.S)
        rootcommentcontent = re.sub(repil, '', rootcommentcontent)
        file.write(rootcommentcontent + '\n')
        print('正在写入评论： ', rootcommentcontent)
file.close()