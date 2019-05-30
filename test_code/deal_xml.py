#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/5/13 20:16
# @Author  : zhaoss
# @FileName: deal_xml.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import glob
import time
import xml.dom.minidom as xml
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def add_child(dom, parent, tag, text=None):
    parent_tag = dom.getElementsByTagName(parent)[0]
    child = dom.createElement(tag)
    if text == None:
        parent_tag.appendChild(child)
    else:
        child.appendChild(dom.createTextNode(text))
        parent_tag.appendChild(child)
    return dom


def add_sample(dom, keywords):
    # 增加sample
    dom = add_child(dom, "annotation", "folder", keywords["folder"])
    dom = add_child(dom, "annotation", "filename", keywords["filename"])
    dom = add_child(dom, "annotation", "path", keywords["path"])
    dom = add_child(dom, "annotation", "source")
    dom = add_child(dom, "source", "database", keywords["database"])
    dom = add_child(dom, "annotation", "size")
    dom = add_child(dom, "size", "width", keywords["width"])
    dom = add_child(dom, "size", "height", keywords["height"])
    dom = add_child(dom, "size", "depth", keywords["depth"])
    dom = add_child(dom, "annotation", "segmented", keywords["segmented"])
    return dom


def add_label(dom, keywords):
    # 增加label
    # 获取根节点
    root_tag = dom.documentElement
    object_tag = dom.createElement("object")
    root_tag.appendChild(object_tag)


    name_tag = dom.createElement("name")
    name_tag.appendChild(dom.createTextNode(keywords["name"]))
    object_tag.appendChild(name_tag)

    pose_tag = dom.createElement("pose")
    pose_tag.appendChild(dom.createTextNode(keywords["pose"]))
    object_tag.appendChild(pose_tag)

    truncated_tag = dom.createElement("truncated")
    truncated_tag.appendChild(dom.createTextNode(keywords["truncated"]))
    object_tag.appendChild(truncated_tag)

    difficult_tag = dom.createElement("difficult")
    difficult_tag.appendChild(dom.createTextNode(keywords["difficult"]))
    object_tag.appendChild(difficult_tag)

    bndbox_tag = dom.createElement("bndbox")
    object_tag.appendChild(bndbox_tag)

    xmin_tag = dom.createElement("xmin")
    xmin_tag.appendChild(dom.createTextNode(keywords["xmin"]))
    bndbox_tag.appendChild(xmin_tag)

    ymin_tag = dom.createElement("ymin")
    ymin_tag.appendChild(dom.createTextNode(keywords["ymin"]))
    bndbox_tag.appendChild(ymin_tag)

    xmax_tag = dom.createElement("xmax")
    xmax_tag.appendChild(dom.createTextNode(keywords["xmax"]))
    bndbox_tag.appendChild(xmax_tag)

    ymax_tag = dom.createElement("ymax")
    ymax_tag.appendChild(dom.createTextNode(keywords["ymax"]))
    bndbox_tag.appendChild(ymax_tag)

    return dom


def main(path):
    # 在内存创建xml文件
    dom = xml.Document()
    # 创建根节点
    root = dom.createElement("annotation")
    # 将根节点添加到xml中
    dom.appendChild(root)
    # 增加sample
    sample_dic = {"folder": "JPEGImages", \
                  "filename": "000001.png", \
                  "path": r"\\192.168.0.234\nydsj\user\ZFF\OCdatasets\OC2019\JPEGImages\000001.png", \
                  "database": "Unknown", \
                  "width": "400", \
                  "height": "408", \
                  "depth": "3", \
                  "segmented": "0"}
    dom = add_sample(dom, sample_dic)
    # 增加标签
    label_dic = {"name": "playground", \
                 "pose": "Unspecified", \
                 "truncated": "0", \
                 "difficult": "0", \
                 "xmin": "46", \
                 "ymin": "73", \
                 "xmax": "374", \
                 "ymax": "251"}
    dom = add_label(dom, label_dic)

    label_dic = {"name": "playground", \
                 "pose": "Unspecified", \
                 "truncated": "0", \
                 "difficult": "0", \
                 "xmin": "466", \
                 "ymin": "73", \
                 "xmax": "374", \
                 "ymax": "251"}
    dom = add_label(dom, label_dic)

    fp = open(path, 'w')
    dom.writexml(fp, indent='\t', addindent='\t', newl='\n', encoding="utf-8")
    dom = None
    return None


if __name__ == '__main__':
    start_time = time.clock()
    xml_path = r"F:\ChangeMonitoring\sample\test\modle_test.xml"
    main(path=xml_path)
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
