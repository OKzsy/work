#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/5/14 17:21
# @Author  : zhaoss
# @FileName: xml_elementree.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import glob
import time
import xml.etree.ElementTree as ET
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def indent(elem, level=0):
    i = "\n" + level * "\t"
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "\t"
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def main(path):
    tree = ET.parse(path)
    root = tree.getroot()
    # 获取节点名字
    print(root.tag)
    # 获取节点属性
    print(root.attrib)
    # 尝试更改xml
    for rank in root.iter('rank'):
        new_rank = int(rank.text) + 1
        rank.text = str(new_rank)
        rank.set("updated", "yes")
    element = ET.SubElement(root, "test_tag")
    element.text = "new"
    # 美化代码
    indent(root)
    tree.write(path, encoding="utf-8", xml_declaration=True, method="xml")
    return None


if __name__ == '__main__':
    start_time = time.clock()
    xml_path = r"F:\ChangeMonitoring\sample\test\out.xml"
    main(path=xml_path)
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
