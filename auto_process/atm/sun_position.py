#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import glob
import time
from datetime import date
import math


def sun_position(Day, Month, Year, GMT, lat, lon, tzone=8):
    deg2rad = math.pi / 180
    lstm = 15 * tzone
    # 计算儒略日
    yy, mm, dd = map(int, [Year, Month, Day])
    d0 = date(yy, 1, 1)
    d1 = date(yy, mm, dd)
    julday = (d1 - d0).days + 1
    # 计算日角b
    b = 360 * (julday - 81) / 365
    b_rad = b * deg2rad
    # 计算时间修正项
    eot = 9.87 * math.sin(2 * b_rad) - 7.53 * math.cos(b_rad) - 1.5 * math.sin(b_rad)
    tc = 4 * (lon - lstm) + eot
    # 将GMT时间转换为以小时为单位的时间
    hour = float(GMT[0:0 + 2]) + tzone
    minutes = float(GMT[2:2 + 2])
    second = float(GMT[5:5 + 2])
    decimal_lt = hour + minutes / 60 + second / 3600
    # 计算时角
    decimal_lst = decimal_lt + tc / 60
    hra = 15 * (decimal_lst - 12)
    # 计算太阳偏角
    sigm_rad = (23.45 * deg2rad) * math.sin((360 * (julday - 81) / 365) * deg2rad)
    # 计算太阳高度角
    sun_elevation_rad = math.asin(math.sin(sigm_rad) * math.sin(lat * deg2rad) +
                                  math.cos(sigm_rad) * math.cos(lat * deg2rad) * math.cos(hra * deg2rad))
    sun_elevation = sun_elevation_rad / deg2rad
    # 计算太阳方位角
    tmp_var = math.sin(sigm_rad) * math.cos(lat * deg2rad) - \
              math.cos(sigm_rad) * math.sin(lat * deg2rad) * math.cos(hra * deg2rad)
    azimuth_rad = math.acos(tmp_var / math.cos(sun_elevation_rad))
    azimuth = azimuth_rad / deg2rad
    # 计算日地距离的倒数
    d = 1 + 0.033 * math.cos(2 * math.pi * julday / 365)
    # 计算日出和日落时间
    sunrise = 12 - math.acos(-math.tan(lat * deg2rad) * math.tan(sigm_rad)) / (15 * deg2rad) - tc / 60
    sunset = 12 + math.acos(-math.tan(lat * deg2rad) * math.tan(sigm_rad)) / (15 * deg2rad) - tc / 60
    return round(sun_elevation, 3), round(azimuth, 3)


def main(Day, Month, Year, GMT, Lat, Lon):
    angle = sun_position(day, month, year, GMT, latitude, longitude)

    return None


if __name__ == '__main__':
    start_time = time.time()
    latitude = 35
    longitude = 114
    year = '2022'
    month = '03'
    day = '08'

    hour = '04'
    minute = '00'
    second = '00'

    GMT = hour + minute + '.' + second

    main(day, month, year, GMT, latitude, longitude)

    end_time = time.time()

    print("time: %.4f secs." % (end_time - start_time))
