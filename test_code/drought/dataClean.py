#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2023/07/12 15:30
# @Author  : zhaoss
# @FileName: dataClean.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
用于从所有土墒仪数据中筛选出和卫星过境时间相匹配的符合要求的数据
Parameters

"""
import os
import time
import json
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta


def main(img, soil, valid):
    """
    综合分析影像信息，土壤墒情仪信息过滤出有效的土壤墒情仪记录
    有效的土壤墒情仪记录：
    1:电压高于10伏
    2:数据记录时间和卫星过境时间最相近且相差在30分钟以内
    """
    # 读取土壤墒情仪数据
    df = pd.read_excel(soil)
    # # 获取指定列数据
    # # 10cm
    # mois_10 = df.loc[:, 'moisture_10'].tolist()
    # mois_10_arr = np.array(mois_10, dtype=np.float16)
    # # 20cm
    # mois_20 = df.loc[:, 'moisture_20'].tolist()
    # mois_20_arr = np.array(mois_20, dtype=np.float16)
    # # 30cm
    # mois_30 = df.loc[:, 'moisture_30'].tolist()
    # mois_30_arr = np.array(mois_30, dtype=np.float16)
    # # 40cm
    # mois_40 = df.loc[:, 'moisture_40'].tolist()
    # mois_40_arr = np.array(mois_40, dtype=np.float16)
    # # 50cm
    # mois_50 = df.loc[:, 'moisture_50'].tolist()
    # mois_50_arr = np.array(mois_50, dtype=np.float16)
    # 获取设备获取数据时间
    mois_time = [y.timestamp() for y in [x.to_pydatetime() for x in df.loc[:, 'time'].tolist()]]
    mois_time_arr = np.array(mois_time, dtype=np.int32)
    # 循环获取影像信息，获取拍摄时间
    # 读取img的信息
    with open(img, 'r') as fq:
        img_messages = json.load(fq)['_default']
    for key, item in img_messages.items():
        observeTimeStr = item['filename'].split('_')[2]
        observeTimedt = datetime.strptime(observeTimeStr, "%Y%m%dT%H%M%S")
        # 将utc时间转换为东8区时间
        observeTimedt = observeTimedt.replace(tzinfo=timezone.utc)
        tzutc_8 = timezone(timedelta(hours=8))
        observeLocTimedt = observeTimedt.astimezone(tzutc_8)
        observeLocstamp = observeLocTimedt.timestamp()
        # 获取最邻近时间
        mosi2imgDiffTime = abs(mois_time_arr - observeLocstamp)
        # 获取最小位置索引
        minDiffIndex = np.argmin(mosi2imgDiffTime)
        pass
    



    return None


if __name__ == '__main__':
    start_time = time.time()
    img_message = r"F:\test\drought\data\record.json"
    soil_message = r"F:\test\drought\data\soil_moisture.xlsx"
    valid_message = r""
    main(img_message, soil_message, valid_message)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))