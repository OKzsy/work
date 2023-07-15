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


def writeData(dstPath, deviceID, moisIDs, imgMessages:dict, deviceTime, mois10, mois20, mois30, mois40, mois50, vol):
    """
    针对每一个设备进行数据筛选
    """
    # 每个设备一个输出文件
    # 列标题为：
    # devID, imgName, devTime, imgTime, voltage, cloud, 10, 20, 30, 40, 50
    dstfile = os.path.join(dstPath, str(deviceID)) + '.txt'
    fp = open(dstfile, 'w')
    fp.write(','.join(['devID', 'imgName', 'devTime', 'imgTime',
             'diffTime', 'voltage', 'cloud', '10', '20', '30', '40', '50']))
    fp.write('\r\n')
    # 从所有数据中筛选单独设备
    devIndex = np.where(moisIDs == deviceID)
    dev10 = mois10[devIndex]
    dev20 = mois20[devIndex]
    dev30 = mois30[devIndex]
    dev40 = mois40[devIndex]
    dev50 = mois50[devIndex]
    devvol = vol[devIndex]
    devTime = deviceTime[devIndex]
    # 依据卫星过境时间匹配最近数据
    for key, item in imgMessages.items():
        observeTimeStr = item['filename'].split('_')[2]
        observeTimedt = datetime.strptime(observeTimeStr, "%Y%m%dT%H%M%S")
        # 将utc时间转换为东8区时间
        observeTimedt = observeTimedt.replace(tzinfo=timezone.utc)
        tzutc_8 = timezone(timedelta(hours=8))
        observeLocTimedt = observeTimedt.astimezone(tzutc_8)
        observeLocstamp = observeLocTimedt.timestamp()
        # 获取最邻近时间
        mosi2imgDiffTime = abs(devTime - observeLocstamp)
        # 获取最小位置索引
        minDiffIndex = np.argmin(mosi2imgDiffTime)
        # 写出对应数据
        diffTime = mosi2imgDiffTime[minDiffIndex]
        valvol = devvol[minDiffIndex]
        # 限定时间差在一天之内, 且设备电压高于5伏
        if diffTime > (24 * 3600) or valvol < 5:
            continue
        devIdStr = str(deviceID)
        imgName = item['filename']
        moisTimeStr = datetime.fromtimestamp(
            devTime[minDiffIndex]).strftime('%Y/%m/%d-%H:%M:%S')
        observeTimeStr = observeLocTimedt.strftime('%Y/%m/%d-%H:%M:%S')
        diffTimeStr = str(diffTime)
        volStr = str(valvol)
        cloudStr = item['cloudcoverpercentage']
        val10Str = str(dev10[minDiffIndex])
        val20Str = str(dev20[minDiffIndex])
        val30Str = str(dev30[minDiffIndex])
        val40Str = str(dev40[minDiffIndex])
        val50Str = str(dev50[minDiffIndex])
        fp.write(','.join([devIdStr, imgName, moisTimeStr, observeTimeStr, diffTimeStr,
                 volStr, cloudStr, val10Str, val20Str, val30Str, val40Str, val50Str]))
        fp.write('\r\n')
        pass
    fp.close()
    return None


def main(img, soil, dst):
    """
    综合分析影像信息，土壤墒情仪信息过滤出有效的土壤墒情仪记录
    有效的土壤墒情仪记录：
    1:电压高于10伏
    2:数据记录时间和卫星过境时间最相近且相差在30分钟以内
    """
    # 设备号
    deviceNum = [16077052,
                 16077053,
                 16077054,
                 16077055,
                 16077056,
                 16077057,
                 16077058,
                 16077059,
                 16077060,
                 16077061,
                 16077062,
                 16077063,
                 16077064,
                 16077065,
                 16077066,
                 21050676,
                 21050677,
                 21050679]
    # 读取土壤墒情仪数据
    df = pd.read_excel(soil)
    # 获取指定列数据
    # 获取设备编号
    moisID = df.loc[:, 'device_id1'].tolist()
    moisID_arr = np.array(moisID, dtype=np.int32)
    # 获取电压
    mois_vol = df.loc[:, 'voltage'].tolist()
    mois_vol_arr = np.array(mois_vol, dtype=np.float16)
    # 10cm
    mois_10 = df.loc[:, 'moisture_10'].tolist()
    mois_10_arr = np.array(mois_10, dtype=np.float16)
    # 20cm
    mois_20 = df.loc[:, 'moisture_20'].tolist()
    mois_20_arr = np.array(mois_20, dtype=np.float16)
    # 30cm
    mois_30 = df.loc[:, 'moisture_30'].tolist()
    mois_30_arr = np.array(mois_30, dtype=np.float16)
    # 40cm
    mois_40 = df.loc[:, 'moisture_40'].tolist()
    mois_40_arr = np.array(mois_40, dtype=np.float16)
    # 50cm
    mois_50 = df.loc[:, 'moisture_50'].tolist()
    mois_50_arr = np.array(mois_50, dtype=np.float16)
    # 获取设备获取数据时间
    mois_time = [y.timestamp() for y in [x.to_pydatetime()
                                         for x in df.loc[:, 'time'].tolist()]]
    mois_time_arr = np.array(mois_time, dtype=np.int32)
    # 循环获取影像信息，获取拍摄时间
    # 读取img的信息
    with open(img, 'r') as fq:
        img_messages = json.load(fq)['_default']
    for dev in deviceNum:
        writeData(dst, dev, moisID_arr, img_messages, mois_time_arr, mois_10_arr,
                  mois_20_arr, mois_30_arr, mois_40_arr, mois_50_arr, mois_vol_arr)

    return None


if __name__ == '__main__':
    start_time = time.time()
    img_message = r"F:\test\drought\data\record.json"
    soil_message = r"F:\test\drought\data\soil_moisture.xlsx"
    valid_message = r"F:\test\drought\data"
    main(img_message, soil_message, valid_message)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
