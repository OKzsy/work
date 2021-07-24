#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2021/2/25 10:00
# @Author  : zhaoss
# @FileName: weather_to_postsql.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import sys
import glob
import time
import psycopg2
import datetime
import fnmatch

city_dict = {
    'changyuan': '长垣',
    'zhengzhou': '郑州',
    'qixian': '淇县',
}


def main(src):
    files = os.listdir(src)
    conn = psycopg2.connect(database="weather_test", user="sa", password="Nydsj@222", host="192.168.0.250", port="5432")
    cur = conn.cursor()
    for file in files:
        ext = os.path.splitext(os.path.basename(file))[1]
        basenames = os.path.splitext(os.path.basename(file))[0].split('-')
        city = city_dict[basenames[0]]
        date_str = '-'.join(basenames[1:4])
        # time_str = ':'.join(basenames[4:])
        if ext == '.txt':
            file_dir = os.path.join(src, file)
            fj = open(file_dir, 'r', newline='')
            lines = fj.readlines()
            fj.close()
            content = []
            # for line in lines[1:]:
            for line in lines:
                tmp = line.strip().split()
                if len(tmp) == 0:
                    continue
                else:
                    content.append(tmp)
        # date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        # idate = 0
        for icon in content:
            # riqi = (date + datetime.timedelta(days=idate)).strftime('%Y-%m-%d')
            # string = "INSERT INTO weather_predict VALUES ('{date_str}','{time_str}','{riqi}','{city}','{weather}'," \
            #          "'{maxtem}','{mintem}','{wind_dir1}','{wind_dir2}','{wind_level}')".format(date_str=date_str,
            #                                                                                     time_str=time_str,
            #                                                                                     riqi=riqi,
            #                                                                                     city=city,
            #                                                                                     weather=icon[1],
            #                                                                                     maxtem=icon[2],
            #                                                                                     mintem=icon[3],
            #                                                                                     wind_dir1=icon[4],
            #                                                                                     wind_dir2=icon[5],
            #                                                                                     wind_level=icon[6])
            string = "INSERT INTO weather_collect VALUES ('{date_str}','{city}','{time}','{tem}','{humidity}'," \
                     "'{rain}','{wind_angle}','{wind_direct}','{wind_level}','{aqi}')".format(date_str=date_str,
                                                                                              city=city,
                                                                                              time=int(icon[0]),
                                                                                              tem=icon[1],
                                                                                              humidity=icon[2],
                                                                                              rain=icon[3],
                                                                                              wind_angle=icon[4],
                                                                                              wind_direct=icon[5],
                                                                                              wind_level=icon[6],
                                                                                              aqi=icon[7])
            # idate += 1
            cur.execute(string)
            conn.commit()
    conn.close()

    return None


if __name__ == '__main__':
    start_time = time.time()
    src_dir = r"F:\weather\changyuan\collect"
    main(src_dir)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
