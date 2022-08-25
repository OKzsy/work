#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2022/08/24 17:35
# @Author  : zhaoss
# @FileName: youdao.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
破解js加密，调用有道网页版进行翻译
Parameters

"""
import os
import time
import requests
import execjs

header = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Connection": "keep-alive",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Cookie": "OUTFOX_SEARCH_USER_ID=936928441@10.110.96.159; OUTFOX_SEARCH_USER_ID_NCOO=1745659914.6973052; ___rl__test__cookies=1661334210316",
    "Host": "fanyi.youdao.com",
    "Origin": "https://fanyi.youdao.com",
    "Referer": "https://fanyi.youdao.com/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest"
}


parms = {
    "i": '',
    "from": "AUTO",
    "to": "AUTO",
    "smartresult": "dict",
    "client": "fanyideskweb",
    "doctype": "json",
    "version": "2.1",
    "keyfrom": "fanyi.web",
    "action": "FY_BY_REALTlME"
}


def main(url):
    word = 'The reality is these places is serious'
    with open(r'encryption.js', mode='r') as f:
        js_code = f.read()
    js = execjs.compile(js_code)
    data = js.call('fanyi', word)
    parms['i'] = word
    parms.update(data)
    # 发送数据
    res = requests.post(url=url, headers=header, params=parms).json()
    # 获取翻译结果
    src = res['translateResult'][0][0]['src']
    tgt = res['translateResult'][0][0]['tgt']
    print('翻译的内容是：{}\n翻译的结果是：{}'.format(src, tgt))
    return None


if __name__ == '__main__':
    start_time = time.time()
    youdao_url = 'https://fanyi.youdao.com/translate_o?smartresult=dict&smartresult=rule'
    main(youdao_url)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
