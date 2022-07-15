#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2022/06/06 16:35
# @Author  : zhaosh
# @FileName: static_weather.py
Description:
根据每天各个整点时刻的气象要素，计算日平均气温，日最高最低气温，日降雨量等气象要素统计信息
Parameters

"""
import os
import time
import numpy as np
from datetime import date
import matplotlib.pyplot as plt


def file_search(folder_path):
    """
    列举出指定文件夹下的所有文件
    """
    files = []
    file_names = os.listdir(folder_path)
    for name in file_names:
        tmp_path = os.path.join(folder_path, name)
        files.append(tmp_path)
    return files


def format_data(file):
    """
    对输入的文件内的数据进行数据清洗和数据格式化
    """
    data = []
    fj = open(file, mode='r', encoding='gbk')
    lines = fj.readlines()
    for line in lines:
        # val_data = [time:int, temperature:int, rain:float]
        val_data = []
        line_data = line.split()
        if int(line_data[1]) == -999:
            continue
        val_data.append(int(line_data[0]))
        val_data.append(int(line_data[1]))
        val_data.append(float(line_data[3]))
        data.append(val_data)
    fj.close()
    return data


def jul_day(fdate):
    # 计算儒略日
    yy, mm, dd = map(int, fdate)
    d0 = date(yy, 1, 1)
    d1 = date(yy, mm, dd)
    julday = (d1 - d0).days + 1
    return julday


def average_temp(dt):
    """
    统计每天的平均气温
    """
    data_time = [hdata[0] for hdata in dt]
    data_tp = [hdata[1] for hdata in dt]
    if {2, 8, 14, 20}.issubset(data_time):
        aver_tp = (data_tp[data_time.index(2)] +
                   data_tp[data_time.index(8)] +
                   data_tp[data_time.index(14)] +
                   data_tp[data_time.index(20)]) / 4
        pass
    else:
        aver_tp = (max(data_tp) + min(data_tp)) / 2
    return aver_tp


def rainfull(dt):
    """
    统计日累计降雨量
    """
    data_rain = [hdata[2] for hdata in dt]
    rain = sum(data_rain)
    return rain


def output(dst, msg):
    """
    将统计结果写出到指定文件
    """
    for day in range(1, 366):
        for item in msg.items():
            result_txt = os.path.join(
                dst, 'weat_info') + '_' + str(item[0]) + '.txt'
            fj = open(result_txt, 'w')
            fj.writelines(['{:<10}'.format(str(title)) for title in ['julday',
                                                                    'ave_temp',
                                                                    'rain_cum']])
            fj.write('\n')
            date_jul = item[1]['date_jul']
            ave_temp = item[1]['ave_temp']
            rain_cum = item[1]['rain_cum']
            num = len(date_jul)
            for i in range(num):
                line = ['{:<10}'.format(str(val)) for val in [date_jul[i],
                                                             ave_temp[i],
                                                            rain_cum[i]]]
                fj.writelines(line)
                fj.write('\n')                                           
            fj.close()
    return None


def main(src, dst):
    # 获取文件列表
    files_path = file_search(src)
    # 创建结果字典
    # msg_dict = {
    #             year:{
    #                  data_jul:[], 儒略日
    #                  ave_tmp:[],  日平均温度
    #                  rain_cum:[]  累积降雨量
    #                   }
    #            }
    msg_dict = {}
    for file_path in files_path:
        # 获取文件对应的日期，并转换为儒略日
        basename = os.path.splitext(os.path.basename(file_path))[0]
        date = basename.split('-')[1:]
        year = int(date[0])
        if year not in list((msg_dict.keys())):
            msg_dict[year] = {
                'date_jul': [],
                'ave_temp': [],
                'rain_cum': []
            }
        julday = jul_day(date)
        msg_dict[year]['date_jul'].append(julday)
        # 逐文件进行数据清洗
        data = format_data(file_path)
        # 计算日平均气温
        day_ave_temp = average_temp(data)
        msg_dict[year]['ave_temp'].append(day_ave_temp)
        # 计算日降雨量
        rain = rainfull(data)
        # 转换为累积降雨量
        if len(msg_dict[year]['rain_cum']) == 0:
            msg_dict[year]['rain_cum'].append(rain)
        else:
            tmp_rain = msg_dict[year]['rain_cum'][-1] + rain
            msg_dict[year]['rain_cum'].append(round(tmp_rain, 3))
    # 写出结果
    output(dst, msg_dict)
    # 绘制结果
    fig, axs = plt.subplots(2, 1)
    x1_date = np.array(msg_dict[2021]['date_jul'])
    x2_date = np.array(msg_dict[2022]['date_jul'])
    y1_temp = np.array(msg_dict[2021]['ave_temp'])
    y2_temp = np.array(msg_dict[2022]['ave_temp'])
    y1_rain = np.array(msg_dict[2021]['rain_cum'])
    y2_rain = np.array(msg_dict[2022]['rain_cum'])
    ax1 = axs[0]
    ax1.plot(x1_date, y1_temp, color='r', label='2021')
    ax1.plot(x2_date, y2_temp, color='g', label='2022')
    ax1.set_title('TEMPERATURE')
    ax1.set_xlim(1, 366)
    ax1.legend()
    ax2 = axs[1]
    ax2.plot(x1_date, y1_rain, color='r', label='2021')
    ax2.plot(x2_date, y2_rain, color='g', label='2022')
    ax2.set_title('RAINFULL')
    ax2.set_xlim(1, 366)
    ax2.legend()
    plt.subplots_adjust(hspace=0.3)
    png = os.path.join(dst, 'result.png')
    plt.savefig(png)
    plt.show()

    return None


if __name__ == '__main__':
    start_time = time.time()
    # 每天气象要素文件夹
    src_folder = r'F:\Coursework\data'
    # 统计结果文件
    dst_file = r'F:\Coursework\result'
    main(src_folder, dst_file)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
