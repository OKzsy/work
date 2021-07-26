#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/7/8 13:22
# @Author  : zhaoss
# @FileName: update_rad_coe.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
利用从资源卫星中心获取的定标系数文件，更新为系统程序可读的综合定标系数文件

Parameters


"""

import os
import glob
import json
import time
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def main(file):
    if not os.path.exists(file):
        rad_coe_dict = {}
    else:
        with open(file) as f_obj:
            rad_coe_dict = json.load(f_obj)
    satellite_prompt = "Please input the satellite ID, "
    satellite_prompt += "\nEnter 'Q' to end the program: "
    sate_active = True
    while sate_active:
        sateID = input(satellite_prompt)
        if sateID.upper() == 'Q':
            sate_active = False
        else:
            sateID_value = rad_coe_dict[sateID] if sateID in rad_coe_dict.keys() else {}
            year_prompt = "Please input the year, "
            year_prompt += "\nEnter 'Q' to end the program: "
            year_active = True
            while year_active:
                yearID = input(year_prompt)
                if yearID.upper() == 'Q':
                    year_active = False
                else:
                    yearID_value = {} if yearID not in sateID_value.keys() else sateID_value[yearID]
                    sensor_prompt = "Please input the sensor ID, "
                    sensor_prompt += "\nEnter 'Q' to end the program: "
                    sensor_active = True
                    while sensor_active:
                        sensorID = input(sensor_prompt)
                        if sensorID.upper() == 'Q':
                            sensor_active = False
                        else:
                            sensorID_value = []
                            rad_prompt = "Please input the radiation coefficient, "
                            rad_prompt += "\nEnter 'Q' to end the program: "
                            rad_active = True
                            while rad_active:
                                rad_coe = input(rad_prompt)
                                if rad_coe.upper() == 'Q':
                                    rad_active = False
                                else:
                                    sensorID_value.append(float(rad_coe))
                            yearID_value[sensorID] = sensorID_value
                    sateID_value[yearID] = yearID_value
                rad_coe_dict[sateID] = sateID_value
    with open(file, "w") as f_obj:
        json.dump(rad_coe_dict, f_obj)
    return None


if __name__ == '__main__':
    start_time = time.clock()
    json_file = r"E:\mypycode\auto_process\atm\6SV\rad_coe.json"
    main(json_file)
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))


