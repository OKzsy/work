#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/5/13 15:15
# @Author  : zhaoss
# @FileName: create_xml.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import glob
import time
from xml.dom import minidom
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def TestAddElement():
    # 在内存中创建一个空的文档
    doc = minidom.Document()
    # 创建一个根节点annotation对象
    root = doc.createElement('annotation')
    # 设置根节点的属性
    root.setAttribute('company', 'xx科技')
    root.setAttribute('address', '科技园区')
    # 将根节点添加到文档对象中
    doc.appendChild(root)

    managerList = [{'name': 'joy', 'age': 27, 'sex': '女'},
                   {'name': 'tom', 'age': 30, 'sex': '男'},
                   {'name': 'ruby', 'age': 29, 'sex': '女'}
                   ]

    for i in managerList:
        nodeManager = doc.createElement('Manager')
        nodeName = doc.createElement('name')
        # 给叶子节点name设置一个文本节点，用于显示文本内容
        nodeName.appendChild(doc.createTextNode(str(i['name'])))

        nodeAge = doc.createElement("age")
        nodeAge.appendChild(doc.createTextNode(str(i["age"])))

        nodeSex = doc.createElement("sex")
        nodeSex.appendChild(doc.createTextNode(str(i["sex"])))

        # 将各叶子节点添加到父节点Manager中，
        # 最后将Manager添加到根节点Managers中
        nodeManager.appendChild(nodeName)
        nodeManager.appendChild(nodeAge)
        nodeManager.appendChild(nodeSex)
        root.appendChild(nodeManager)
    return doc

def main():
    # 开始写xml文档
    doc = TestAddElement()
    fp = open(r'F:\ChangeMonitoring\sample\test\Manager.xml', 'w', encoding="utf-8")
    doc.writexml(fp, indent='\t', addindent='\t', newl='\n', encoding="utf-8")
    fp.close()



if __name__ == '__main__':
    start_time = time.clock()
    main()
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))


