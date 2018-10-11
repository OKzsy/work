#!/usr/bin/env python3
# -*- coding:utf-8 -*-


import json
import os
import math


# json_path = r"F:\project\data\skysat\xiangcheng\planet_order_217674\20180718_054452_ssc10d1_0019\20180718_054452_" \
#             r"ssc10d1_0019_metadata.json"
#
# with open(json_path) as json_obj:
#     json_txt = json.load(json_obj)
#
# print(json_txt['properties']['cloud_cover'])


def searchFile(start_dir, target):
    os.chdir(start_dir)
    for each_file in os.listdir(os.curdir):
        ext = os.path.splitext(each_file)[1]
        if ext in target:
            py_list.append(os.getcwd() + os.sep + each_file)
        if os.path.isdir(each_file):
            searchFile(each_file, target)
            os.chdir(os.pardir)


def get_pars_from_json(json_file):
    deg2radian = math.pi / 180
    pars_file = r"F:\project\data\skysat\20180605_055536_ssc6d1_0011\pars.txt"
    with open(json_file) as json_obj:
        json_txt = json.load(json_obj)

    sat_ID = json_txt['properties']['satellite_id']
    sensorID = json_txt['id']
    ID_strs = str(sensorID).split('_')
    imgID = ID_strs[2] + '_' + ID_strs[3]
    sun_zen = round(90.0 - float(json_txt['properties']['sun_elevation']), 4)
    sun_azi = json_txt['properties']['sun_azimuth']
    view_angle = float(json_txt['properties']['view_angle'])
    satelliteAltitude = sat_alt[sat_ID]
    sat_zen = round(math.asin(((6371 + satelliteAltitude) / 6371) * math.sin(view_angle * deg2radian)) / deg2radian, 4)
    sat_azi = json_txt['properties']['satellite_azimuth']

    list_1 = [sat_ID, imgID, ID_strs[0], str(sun_zen), str(sun_azi), str(sat_zen), str(sat_azi), str(satelliteAltitude)]
    list_out = ["{:<10s}".format(name) for name in list_1]

    str_2 = '   '.join(list_out)

    pars_obj = open(pars_file, 'a')
    pars_obj.write(str_2 + '\n')
    pars_obj.close()


start_dir = r"F:\project\data\skysat\20180605_055536_ssc6d1_0011"
program_dir = os.getcwd()
target = ['.json']
py_list = []
sat_alt = {'SS01': 450, 'SS02': 450, 'SSC3': 500, 'SSC4': 500, 'SSC5': 500, 'SSC6': 500, 'SSC7': 500, 'SSC8': 503.5,
           'SSC9': 503.5, 'SSC10': 503.5, 'SSC11': 503.5, 'SSC12': 503.5, 'SSC13': 503.5}
searchFile(start_dir, target)

for file in py_list:
    get_pars_from_json(file)
