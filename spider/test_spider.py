#!/usr/bin/env/ python3
# -*- coding:utf-8 -*-

import requests
from requests import exceptions
import os

# resq = requests.get("https://www.baidu.com")
# # 查看相应类型
# print(type(resq))
# # 输出状态吗
# print(resq.status_code)
# # 输出相应类型 text
# print(type(resq.text))
# # 输出相应内容
# print(resq.text.encode("utf-8"))
# # 输出cookies
# print(resq.cookies)
# get 请求
# resq = requests.get('http://httpbin.org/get')
# print(resq.text)
# # 带参数请求
# resq = requests.get("http://httpbin.org/get?name=jyx&age=18")
# print(resq.text)
# # 封装参数请求
# param = {"name": 'zss',
#         "age": "19"}
# resq = requests.get('http://httpbin.org/get', params=param)
# print(type(resq.text))
# print(resq.json())
# resq = requests.get("http://github.com/favicon.ico")
# print(type(resq.text), type(resq.content))
# # 输出相应内容
# print(resq.text)
# # 输出相应二进制内容
# dir_path = r"e:\PythonCode\pic"
# ico = os.path.join(dir_path,'favicon.ico')
# with open(ico, 'wb') as f:
#     f.write(resq.content)
# f.close
headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36"}
# resq = requests.get("https://www.zhihu.com/explore", headers=headers)
# print(resq.text)
# 使用post
data = {'name':"zss", "age":"20"}
resp = requests.post('http://httpbin.org/post', data=data, headers=headers)
print(resp.text)