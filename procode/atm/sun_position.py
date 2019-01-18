#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import glob
import time
import datetime
import math


class Julday:

    def __init__(self, year, month, day):
        self.year = int(year)
        self.month = int(month)
        self.day = int(day)

    def cal_julday(self):
        # 利用datetime库中的datetime函数的方法快速计算需要日期的儒略日
        current = datetime.datetime(self.year, self.month, self.day)
        re_julday = current.timetuple().tm_yday
        return re_julday


def sun_position(Day, Month, Year, GMT, latitude, longitude):
    deg2radian = math.pi / 180
    # 计算儒略日
    julday = Julday(Year, Month, Day).cal_julday()
    # 计算日角D
    Day_angle = 2 * math.pi * (julday - 1) / 365
    # 计算时间修正项
    Et = (0.000075 + 0.001868 * math.cos(Day_angle) - 0.032077 * math.sin(Day_angle) - 0.014615 * math.cos(
        2 * Day_angle) - 0.04089 * math.sin(2 * Day_angle)) * 229.18 / 60
    # 将GMT时间转换为以小时为单位的时间
    hour = float(GMT[0:0 + 2])
    minute = float(GMT[2:2 + 2])
    second = float(GMT[5:5 + 2])
    UTC = hour + minute / 60 + second / 3600
    # 计算时角
    h = (UTC + longitude / 15 + Et - 12) * 15
    h = h * deg2radian
    # 计算太阳倾角
    ED = 0.006918 - 0.399912 * math.cos(Day_angle) + 0.070257 * math.sin(Day_angle) - 0.006758 * math.cos(
        2 * Day_angle) + 0.000907 * math.sin(2 * Day_angle) - 0.002697 * math.cos(3 * Day_angle) + 0.00148 * math.sin(
        3 * Day_angle)
    # 计算太阳高度角
    elevation_angle = math.acos(
        math.sin(latitude * deg2radian) * math.sin(ED) + math.cos(latitude * deg2radian) * math.cos(ED) * math.cos(h))
    elevation_angle = elevation_angle / deg2radian
    return elevation_angle


def main(Day, Month, Year, GMT, Lat, Lon):
    angle = sun_position(day, month, year, GMT, latitude, longitude)

    return None


if __name__ == '__main__':
    start_time = time.clock()
    latitude = 34.8818
    longitude = 113.144
    year = '2017'
    month = '10'
    day = '20'

    hour = '03'
    minute = '41'
    second = '06'

    GMT = hour + minute + '.' + second

    main(day, month, year, GMT, latitude, longitude)

    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
