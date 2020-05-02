#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/8/30 10:04
# @Author  : zhaoss
# @FileName: TranslateFromYoudao.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import sys
import glob
import time
import fnmatch
import numpy as np
import requests
import json

def main(url, words):
    Form_data = {'i': words, 'from': 'AUTO', 'to': 'AUTO', 'smartresult': 'dict', 'client': 'fanyideskweb', \
                 'salt': '15679987359902', 'sign': '1872819767ab225677fdbe7fb213e01d', 'ts': '1567998735990', \
                 'bv': '9915c65c9e78cfd742d6a24e66b85108', 'doctype': 'json', 'version': '2.1', 'keyfrom': 'fanyi.web', \
                 'action': 'FY_BY_REALTlME'}
    response = requests.post(url, data=Form_data)
    content = json.loads(response.text)
    print(content['translateResult'][0][0]['tgt'])
    return None


if __name__ == '__main__':
    start_time = time.clock()
    url = "http://fanyi.youdao.com/translate?smartresult=dict&smartresult=rule"
    words = 'exception'
    end_time = time.clock()
    main(url, words)
    print("time: %.4f secs." % (end_time - start_time))
