#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/9/26 11:01
# @Author  : zhaoss
# @FileName: test_polder.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import requests

headers = {
    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36",
    'Cookie': '_saml_idp=aHR0cHM6Ly9sb2dpbi5ncmFzcC1vcGVuLmNvbS9hdXRoL3JlYWxtcy9ncmFzcC1jbG91ZA%3D%3D; 29338da4eeedaf3c31ecd6381288dd17=6f7f1fc297e09ab39e5dc01deaf4d3c1'
}
url = "https://download.grasp-cloud.com/Shibboleth.sso/SAML2/POST"
s = requests.session()
r = s.post(url, headers=headers)
print(r.text())
