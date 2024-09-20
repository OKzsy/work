#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2024/01/13 14:23
# @Author  : zhaoss
# @FileName: Image_lossless_scaling.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:

Parameters

"""
import os
import time
import base64
import urllib
import requests
import json
from PIL import Image
from io import BytesIO

API_KEY = "AKTnF4qPiQrtmsXHnrKnCxSh"
SECRET_KEY = "0gaug8udyfTDE5n1xTFCGGYl9kNGmaG5"


def main(src_file, dst_path):
    basename = os.path.basename(src_file)

    url = "https://aip.baidubce.com/rest/2.0/image-process/v1/image_quality_enhance?access_token=" + get_access_token()

    img_base64 = get_file_content_as_base64(src_file, True)
    payload = 'image=' + img_base64
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    new_img_base64 = json.loads(response.text)['image']
    dst_file = os.path.join(dst_path, basename)
    save_base64_content_to_file(new_img_base64, dst_file)

def get_file_content_as_base64(path, urlencoded=False):
    """
    获取文件base64编码
    :param path: 文件路径
    :param urlencoded: 是否对结果进行urlencoded 
    :return: base64编码信息
    """
    with open(path, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf8")
        if urlencoded:
            content = urllib.parse.quote_plus(content)
    return content


def get_access_token():
    """
    使用 AK,SK 生成鉴权签名(Access Token)
    :return: access_token,或是None(如果错误)
    """
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {"grant_type": "client_credentials",
              "client_id": API_KEY, "client_secret": SECRET_KEY}
    return str(requests.post(url, params=params).json().get("access_token"))

def save_base64_content_to_file(base64_str, file_path):
    """
    获取文件base64编码
    :param path: 输出文件路径
    :return: None
    """
    img_data = base64.b64decode(base64_str)
    img = Image.open(BytesIO(img_data))
    img.save(file_path)
    return None


if __name__ == '__main__':

    src_img = r"F:\空天所\巫老师本子照片处理\项目图片\img_10.jpg"
    dst_img = r"F:\空天所\巫老师本子照片处理\项目图片\xin"
    start_time = time.time()
    main(src_file=src_img, dst_path=dst_img)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))