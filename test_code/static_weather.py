#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2022/06/06 16:35
# @Author  : zhaoss
# @FileName: static_weather.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
根据每天各个整点时刻的气象要素，计算日平均气温，日最高最低气温，日降雨量等气象要素统计信息
Parameters

"""
import os
import time


def file_search(path):
    """
    列举出指定文件夹下的所有文件
    """
    files = []
    file_names = os.listdir(path)
    for file in file_names:
        files.append(os.path.join(path, file))
    return files


def format_data():
    """
    对输入的文件内的数据进行数据清洗和数据格式化
    """

    data = []
    return data


def average_temp():
    """
    统计每天的平均气温
    """
    ave_temp = 0
    return ave_temp


def cum_rainfull():
    """
    统计日累计降雨量
    """
    cum_rain = 0
    return cum_rain


def static_maximum_temp():
    """
    统计日最值气温
    """
    maximum_temp = []
    return maximum_temp


def output():
    """
    将统计结果写出到指定文件
    """
    return None


def main(src):
    files_path = file_search(src)
    for file in files_path:
        format_data(file)
    return None


if __name__ == '__main__':
    start_time = time.time()
    # 每天气象要素文件夹
    src_folder = r'F:\test_data\ESUN_data'
    # 统计结果文件
    dst_file = r''
    main(src_folder)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
