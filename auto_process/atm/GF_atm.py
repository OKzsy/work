#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/6/28 10:56
# @Author  : zhaoss
# @FileName: GF_atm.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import sys
import subprocess
import glob
import fnmatch
import math
import json
import xml.dom.minidom
import numba as nb
import numpy as np
import time
from datetime import date
from scipy import interpolate

from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


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
    return 90 - round(sun_elevation, 3), round(azimuth, 3)


def searchfiles(dirpath, partfileinfo='*', recursive=False):
    """列出符合条件的文件（包含路径），默认不进行递归查询，当recursive为True时同时查询子文件夹"""
    # 定义结果输出列表
    filelist = []
    # 列出根目录下包含文件夹在内的所有文件目录
    pathlist = glob.glob(os.path.join(os.path.sep, dirpath, "*"))
    # 逐文件进行判断
    for mpath in pathlist:
        if os.path.isdir(mpath):
            # 默认不判断子文件夹
            if recursive:
                filelist += searchfiles(mpath, partfileinfo, recursive)
        elif fnmatch.fnmatch(os.path.basename(mpath), partfileinfo):
            filelist.append(mpath)
        # 如果mpath为子文件夹，则进行递归调用，判断子文件夹下的文件

    return filelist


def file_basename(path, RemoveSuffix=''):
    """去除文件名后部去除任意指定的字符串。"""
    if not os.path.isfile(path):
        raise Exception("The path is not a file!")
    if not RemoveSuffix:
        return os.path.basename(path)
    else:
        basename = os.path.basename(path)
        return basename[:basename.index(RemoveSuffix)]


def GET_XMLELEMENTS(oDocument, IDtxt):
    # 获取指定IDtxt的值
    oNodeList = oDocument.getElementsByTagName(IDtxt)
    # 定义返回的列表
    strDT = []
    if oNodeList.length == 1:
        return oNodeList[0].firstChild.data
    else:
        for node in oNodeList:
            strDT.append(node.firstChild.data)
        return strDT


def SECTRUM(wlinf, wlsup, band, fun_path, senID, satID):
    # 对光谱进行插值
    wlinf = wlinf * 1000
    wlsup = wlsup * 1000
    step = 2.5
    num = math.ceil((wlsup - wlinf) * 1. / step) + 1
    xout = np.arange(num, dtype='float64') * step + wlinf  # 类似于idl中的make_array中使用/index和INCREMENT=step功能
    ori_spec = fun_path + os.sep + '6SV' + os.sep + 'spec' + os.sep + satID + os.sep + senID + '.txt'
    # 将光谱度如矩阵用于插值
    spec_lib = np.loadtxt(ori_spec)
    wave = spec_lib[:, 0]
    band_value = spec_lib[:, band + 1]
    fq = interpolate.interp1d(wave, band_value, kind='quadratic')
    res = fq(xout)
    return res


def corner_to_geo(sample, line, dataset):
    # 计算指定行,列号的地理坐标
    Geo_t = dataset.GetGeoTransform()
    # 计算地理坐标
    geoX = Geo_t[0] + sample * Geo_t[1]
    geoY = Geo_t[3] + line * Geo_t[5]
    return geoX, geoY


def reproject_dataset(src_ds, new_x_size, new_y_size):
    # 定义目标投影
    oSRS = osr.SpatialReference()
    oSRS.SetWellKnownGeogCS("WGS84")

    # 获取原始投影
    src_prj = src_ds.GetProjection()
    oSRC = osr.SpatialReference()
    oSRC.ImportFromWkt(src_prj)
    # 测试投影转换
    oSRC.SetTOWGS84(0, 0, 0)
    tx = osr.CoordinateTransformation(oSRC, oSRS)

    # 获取原始影像的放射变换参数
    geo_t = src_ds.GetGeoTransform()
    x_size = src_ds.RasterXSize  # Raster xsize
    y_size = src_ds.RasterYSize  # Raster ysize
    bandCount = src_ds.RasterCount  # Band Count
    dataType = src_ds.GetRasterBand(1).DataType  # Data Type
    # 获取影像的四个角点地理坐标
    # 左上
    old_ulx, old_uly = corner_to_geo(0, 0, src_ds)
    # 右上
    old_urx, old_ury = corner_to_geo(x_size, 0, src_ds)
    # 左下
    old_dlx, old_dly = corner_to_geo(0, y_size, src_ds)
    # 右下
    old_drx, old_dry = corner_to_geo(x_size, y_size, src_ds)

    # 计算出新影像的边界
    # 左上
    (new_ulx, new_uly, new_ulz) = tx.TransformPoint(old_ulx, old_uly, 0)
    # 右上
    (new_urx, new_ury, new_urz) = tx.TransformPoint(old_urx, old_ury, 0)
    # 左下
    (new_dlx, new_dly, new_dlz) = tx.TransformPoint(old_dlx, old_dly, 0)
    # 右下
    (new_drx, new_dry, new_drz) = tx.TransformPoint(old_drx, old_dry, 0)
    # 统计出新影像的范围
    # 左上经度
    ulx = min(new_ulx, new_dlx)
    # 左上纬度
    uly = max(new_uly, new_ury)
    # 右下经度
    lrx = max(new_urx, new_drx)
    # 右下纬度
    lry = min(new_dly, new_dry)

    # 创建重投影后新影像的存储位置
    mem_drv = gdal.GetDriverByName('MEM')
    # 根据计算的参数创建存储空间
    dest = mem_drv.Create('', int((lrx - ulx) / new_x_size), \
                          int((uly - lry) / new_y_size), bandCount, dataType)
    # 计算新的放射变换参数
    new_geo = (ulx, new_x_size, geo_t[2], uly, geo_t[4], -new_y_size)
    # 为重投影结果设置空间参考
    dest.SetGeoTransform(new_geo)
    dest.SetProjection(oSRS.ExportToWkt())

    # 执行重投影和重采样
    print('Begin to reprojection and resample!')
    res = gdal.ReprojectImage(src_ds, dest, \
                              src_prj, oSRS.ExportToWkt(), \
                              gdal.GRA_Bilinear, callback=progress)
    return dest


def get_rad_coe(satID, year, senID, function_position):
    # GF定标系数文件
    rad_coe_path = os.path.join(function_position, '6SV', 'rad_coe.json')
    with open(rad_coe_path) as f_obj:
        rad_coe_dict = json.load(f_obj)
    # 获取satID下所有定标系数的年份
    year_list = [int(x) for x in rad_coe_dict[satID].keys()]
    if int(year) in year_list:
        rad_coe = rad_coe_dict[satID][year][senID]
    elif (int(year) > max(year_list)) and (int(year) - max(year_list) == 1):
        year = str(max(year_list))
        rad_coe = rad_coe_dict[satID][year][senID]
    else:
        rad_coe = None
    return rad_coe


# @nb.jit
def ATM_CORRECT(source_ds, img_out_path, atm_coe, rad_coe, satID):
    # 对影像进行大气校正
    # 大气校正系数
    # xa, xb, xc
    # y = xa * (measured radiance) - xb
    # acr = y / (1. + xc * y)
    # atm_coe = ['Blue', 'Green', 'Red', 'Ninf']
    # 获取投影和放射变换参数
    source_prj = source_ds.GetProjection()
    source_geo = source_ds.GetGeoTransform()
    band_count = source_ds.RasterCount
    # 获取影像的NoData值
    source_in_band = source_ds.GetRasterBand(1)
    a_nodata = source_in_band.GetNoDataValue()
    if a_nodata == None:
        a_nodata = 0
    if band_count == 1:
        # 获取数据
        pan = source_ds.GetRasterBand(1).ReadAsArray()
        zero_index = np.where(pan == a_nodata)
        # 辐射定标至表观辐亮度
        pan_ref = pan * rad_coe[0]
        pan = None
        # 大气校正
        # pan
        y = atm_coe[0, 0] * pan_ref - atm_coe[0, 1]
        pan_ref = None
        pan_suf_ref = y / (1.0 + atm_coe[0, 2] * y)
        pan_suf_ref[zero_index] = 0
        pan_suf_ref = (pan_suf_ref * 10000).round()
        # 创建临时数据集用于存放大气校正结果
        tmp_driver = gdal.GetDriverByName('MEM')
        atm_ds = tmp_driver.CreateCopy(" ", source_ds)
        atm_ds.GetRasterBand(1).WriteArray(pan_suf_ref)
        pan_suf_ref = None
        # 进行重投影和重采样
        if satID in ['GF1', 'GF1B', 'GF1C', 'GF1D', 'GF6']:
            new_xs = 0.00002
            new_ys = 0.00002
        else:
            new_xs = 0.00001
            new_ys = 0.00001
        dest = reproject_dataset(atm_ds, new_xs, new_ys)
        # del atm_ds
        # 存储经大气校正的结果
        print('Store atmospheric correction results!')
        driver = gdal.GetDriverByName("GTiff")
        dst_ds = driver.CreateCopy(img_out_path, dest, callback=progress)
    else:
        # 获取数据
        Blue_band = source_ds.GetRasterBand(1).ReadAsArray()
        zero_index = np.where(Blue_band == a_nodata)
        Green_band = source_ds.GetRasterBand(2).ReadAsArray()
        Red_band = source_ds.GetRasterBand(3).ReadAsArray()
        Inf_band = source_ds.GetRasterBand(4).ReadAsArray()
        # 判断是否缺少波段
        if Blue_band.max() == 0 or Green_band.max() == 0 or Red_band.max() == 0 or Inf_band.max() == 0:
            print('The {} file has no inf band'.format('basename'))
            return
        # 辐射定标至表观反射率
        Blue_ref = Blue_band * rad_coe[1]
        Green_ref = Green_band * rad_coe[2]
        Red_ref = Red_band * rad_coe[3]
        Inf_ref = Inf_band * rad_coe[4]
        # 大气校正
        # Blue
        y = atm_coe[1, 0] * Blue_ref - atm_coe[1, 1]
        Blue_suf_ref = y / (1.0 + atm_coe[1, 2] * y)
        Blue_suf_ref[zero_index] = 0
        Blue_suf_ref = (Blue_suf_ref * 10000).round()
        # Green
        y = atm_coe[2, 0] * Green_ref - atm_coe[2, 1]
        Green_suf_ref = y / (1.0 + atm_coe[2, 2] * y)
        Green_suf_ref[zero_index] = 0
        Green_suf_ref = (Green_suf_ref * 10000).round()
        # Red
        y = atm_coe[3, 0] * Red_ref - atm_coe[3, 1]
        Red_suf_ref = y / (1.0 + atm_coe[3, 2] * y)
        Red_suf_ref[zero_index] = 0
        Red_suf_ref = (Red_suf_ref * 10000).round()
        # Inf
        y = atm_coe[4, 0] * Inf_ref - atm_coe[4, 1]
        Inf_suf_ref = y / (1.0 + atm_coe[4, 2] * y)
        Inf_suf_ref[zero_index] = 0
        Inf_suf_ref = (Inf_suf_ref * 10000).round()
        # 创建临时数据集用于存放大气校正结果
        tmp_driver = gdal.GetDriverByName('MEM')
        atm_ds = tmp_driver.CreateCopy(" ", source_ds)
        atm_ds.GetRasterBand(1).WriteArray(Blue_suf_ref)
        atm_ds.GetRasterBand(2).WriteArray(Green_suf_ref)
        atm_ds.GetRasterBand(3).WriteArray(Red_suf_ref)
        atm_ds.GetRasterBand(4).WriteArray(Inf_suf_ref)
        # 进行重投影和重采样
        if satID in ['GF1', 'GF1B', 'GF1C', 'GF1D', 'GF6']:
            new_xs = 0.00008
            new_ys = 0.00008
        else:
            new_xs = 0.00004
            new_ys = 0.00004
        dest = reproject_dataset(atm_ds, new_xs, new_ys)
        # 存储经大气校正的结果
        print('Store atmospheric correction results!')
        driver = gdal.GetDriverByName("GTiff")
        dst_ds = driver.CreateCopy(img_out_path, dest, callback=progress)
    # 释放资源
    atm_ds = None
    dst_ds = None
    source_ds = None
    dest = None
    return None


def get_aod(img_ds, aod_file):
    img_geo = img_ds.GetGeoTransform()
    xsize = img_ds.RasterXSize
    ysize = img_ds.RasterYSize
    aod_ds = gdal.Open(aod_file)
    aod_geo = aod_ds.GetGeoTransform()
    aod_inv_geo = gdal.InvGeoTransform(aod_geo)
    # 左上经度
    ulx = img_geo[0]
    # 左上纬度
    uly = img_geo[3]
    # 右下经度
    lrx = corner_to_geo(xsize, ysize, img_ds)[0]
    # 右下纬度
    lry = corner_to_geo(xsize, ysize, img_ds)[1]
    extent = [ulx, uly, lrx, lry]
    # 计算在aod影像上的行列号
    off_ulx, off_uly = map(int, gdal.ApplyGeoTransform(aod_inv_geo, extent[0], extent[1]))
    off_drx, off_dry = map(math.ceil, gdal.ApplyGeoTransform(aod_inv_geo, extent[2], extent[3]))
    columns = off_drx - off_ulx
    rows = off_dry - off_uly
    aod = aod_ds.ReadAsArray(off_ulx, off_uly, columns, rows)
    numbers = columns * rows
    spec_num = np.where(aod == -9999)[0].shape[0]
    if spec_num == numbers:
        mean_aod = 0.6
    else:
        mean_aod = np.mean(aod[np.where(aod != -9999)]) * 0.001
    aod_ds = None
    return mean_aod


def main(file_path, out_path, partfileinfo='*.tif'):
    # 注册所有gdal的驱动
    gdal.AllRegister()
    gdal.SetConfigOption("gdal_FILENAME_IS_UTF8", "YES")
    # 获取当前工作路径
    function_position = os.path.dirname(os.path.abspath(sys.argv[0]))
    # 需要大气校正影像路径
    original_dir_path = file_path
    original_imgs = searchfiles(original_dir_path, partfileinfo, recursive=True)
    # 定义卫星通道参数，单位微米
    w = [[0.45, 0.890], [0.45, 0.52], [0.52, 0.59], [0.63, 0.69], [0.77, 0.89]]
    for num_file in range(len(original_imgs)):
        # 开始循环单个文件处理
        input = original_imgs[num_file]
        # 打开影像
        input_ds = gdal.Open(input)
        band_count = input_ds.RasterCount
        input_geo = input_ds.GetGeoTransform()
        xsize = input_ds.RasterXSize
        ysize = input_ds.RasterYSize
        # 获取文件根目录
        file_dir = os.path.dirname(input)
        # 文件名
        basename = os.path.splitext(os.path.basename(input))[0]
        # 获取影像元数据路径
        # xml路径
        xmlpath = file_dir + os.sep + basename + '.xml'
        if not os.path.exists(xmlpath):
            print('The file: {0} has no xml!'.format(input))
            continue
        # 打开xml文件
        oDocument = xml.dom.minidom.parse(xmlpath).documentElement
        ID = 'SatelliteID'  # 卫星编号
        SatelliteID = GET_XMLELEMENTS(oDocument, ID)
        ID = 'ProductID'  # 产品号
        ProductID = GET_XMLELEMENTS(oDocument, ID)
        ID = 'SensorID'  # 传感器号
        SensorID = GET_XMLELEMENTS(oDocument, ID)
        igeom = 0  # 自定义几何条件
        # 计算太阳天顶角和方位角
        ID = 'ReceiveTime'  # 影像获取时间
        ReceiveTime = GET_XMLELEMENTS(oDocument, ID)
        ReceiveTimes = ReceiveTime.split(' ')
        date = ReceiveTimes[0].split('-')
        time = ReceiveTimes[1].split(':')
        year = date[0]  # 年份
        month = date[1]  # 月份
        day = date[2]  # 日期
        # 组合对应aod文件名字
        aod_path = os.path.join(function_position, '6SV', 'tif_aod')
        basename_aod = "{:0>4d}".format(int(year)) + "{:0>2d}".format(int(month)) + "{:0>2d}".format(int(day)) + '.tif'
        aod_file = os.path.join(aod_path, basename_aod)
        hour = time[0]  # 小时
        minute = time[1]  # 分钟
        second = time[2]  # 秒
        GMTtime = "{:0>2d}".format(int(hour)) + "{:0>2d}".format(int(minute)) + "." + "{:0>2d}".format(
            int(float(second)))
        # 获取四角坐标
        # ID = 'TopLeftLatitude'
        # TopLeftLatitude = float(GET_XMLELEMENTS(oDocument, ID))
        # ID = 'TopLeftLongitude'
        # TopLeftLongitude = float(GET_XMLELEMENTS(oDocument, ID))
        # ID = 'BottomRightLatitude'
        # BottomRightLatitude = float(GET_XMLELEMENTS(oDocument, ID))
        # ID = 'BottomRightLongitude'
        # BottomRightLongitude = float(GET_XMLELEMENTS(oDocument, ID))
        # 为了避免xml记录错误，通过影像计算交点坐标
        TopLeftLongitude = input_geo[0]
        TopLeftLatitude = input_geo[3]
        BottomRightLongitude, BottomRightLatitude = corner_to_geo(xsize, ysize, input_ds)
        # 中心经纬度
        lat = (TopLeftLatitude + BottomRightLatitude) * 1.0 / 2
        lon = (TopLeftLongitude + BottomRightLongitude) * 1.0 / 2
        # 计算影像中心的太阳天顶角
        otSunZA = sun_position(day, month, year, GMTtime, lat, lon)
        zsun = otSunZA
        # 获取太阳方位角
        ID = 'SolarAzimuth'
        asun = float(GET_XMLELEMENTS(oDocument, ID))  # 太阳方位角
        ID = 'SatelliteZenith'
        tmp_zsat = float(GET_XMLELEMENTS(oDocument, ID))
        if SatelliteID in ['GF1B', 'GF1C', 'GF1D', 'GF6']:
            zsat = tmp_zsat  # 卫星天顶角
        else:
            zsat = 90.0 - tmp_zsat  # 卫星天顶角
        ID = 'SatelliteAzimuth'
        asat = float(GET_XMLELEMENTS(oDocument, ID))  # 卫星方位角

        if (int(month) >= 4) and (int(month) <= 9):
            idatm = 2  # 大气模式中纬度夏季
        else:
            idatm = 3  # 大气模式中纬度冬季
        iaer = 1  # 气溶胶模式大陆型
        v = 0  # 选择输入能见度还是气溶胶光学厚度
        if not os.path.exists(aod_file):
            sys.exit("The aod file of {} doesn't exit!".format(os.path.basename(aod_file)))
        tao = round(get_aod(input_ds, aod_file), 3)  # 550nm气溶胶光学厚度
        print('AOD:{}'.format(tao))
        xps = 0  # 目标物高度
        xpp = -631  # 星测
        iwave = 1  # 自定义1输入波段范围和反射相函数
        inhomo = 0  # 地表反射率均一地表
        idirect = 0  # 无方向效应
        igroun = 1  # 绿色植被
        atm = 0  # Atm.correction Lambertian
        radiance = -0.5  # radiance(positivevalue)
        # 更改程序工作路径
        os.chdir(os.path.join(function_position, '6SV'))
        # 输出辐射校正系数
        outcoe = os.path.join(function_position, '6SV', 'outcoe', SensorID) + '-' + ProductID + '.txt'
        # 打开辐射校正系数文件用于写入辐射校正系数
        lun_coe = open(outcoe, 'w', newline=None)
        if band_count != 1:
            band_count = 5
        coearr = np.full((band_count, 3), -999.0, dtype='float16')
        for a in range(band_count):  # 循环处理各个波段
            band = ['pan', 'Blue', 'Green', 'Red', 'Ninf']
            txtname = 'in.txt'
            lun = open(txtname, 'w', newline=None)
            lun.write('{:<3d} {} {}'.format(igeom, '(User defined)', '\n'))
            lun.write(
                '{:<10.5f} {:<10.5f} {:<10.5f} {:<10.5f} {:<3d} {:<3d} {} {}'.format(zsun, asun, zsat, asat, int(month),
                                                                                     int(day),
                                                                                     '(geometrical conditions)', '\n'))
            lun.write('{:<3d} {} {}'.format(idatm, 'Midlatitude Summer', '\n'))
            lun.write('{:<3d} {} {}'.format(iaer, 'Continental Model', '\n'))
            lun.write('{:<3d} {}'.format(v, '\n'))
            lun.write('{:<8.4f} {} {}'.format(tao, 'value', '\n'))
            lun.write('{:<3d} {} {}'.format(xps, '(target level)', '\n'))
            lun.write('{:<3d} {} {}'.format(xpp, '(sensor level)', '\n'))
            lun.write('{:<3d} {} {}'.format(iwave, "User's defined filtered function", '\n'))
            lun.write('{:<7.3} {:<7.3} {}'.format(w[a][0], w[a][1], '\n'))
            res = SECTRUM(w[a][0], w[a][1], a, function_position, SensorID, SatelliteID)
            for spec_value in res:
                lun.write('{:<10.6f} {}'.format(spec_value, '\n'))
            lun.write('{:<3d} {} {}'.format(inhomo, 'Homogeneous surface', '\n'))
            lun.write('{:<3d} {} {}'.format(idirect, 'No directional effects', '\n'))
            lun.write('{:<3d} {} {}'.format(igroun, '(mean spectral value)', '\n'))
            lun.write('{:<3d} {} {}'.format(atm, 'Atm. correction Lambertian', '\n'))
            lun.write('{:<5.1f} {} {}'.format(radiance, 'reflectance (negative value)', '\n'))
            # 关闭参数输入文件
            lun.close()
            subprocess.call('6sv1-run<in.txt>out.txt', shell=True)
            txtname = 'out.txt'
            with open(txtname, 'rt') as out_6sv:
                temp = out_6sv.readlines()
            # 获取大气校正系数
            coe = temp[163][49: 49 + 25]
            # 转换为矩阵形式
            coes = np.array(coe.split(), dtype='float16')
            # 存储该影像对应波段的大气校正系数
            coearr[a, :] = coes
            lun_coe.write(coe + '\n')
            os.remove(txtname)
        # 关闭文件
        lun_coe.close()

        # 对影像进行大气校正
        out_file_name = basename
        out_file = out_path + os.sep + out_file_name + '_atm.tif'
        # 获取该景影像的辐射定标系数
        # 高分定标系数
        # [PAN, Band1, Band2, Band3, Band4]
        radiance_coefficient = get_rad_coe(SatelliteID, year, SensorID, function_position)
        if radiance_coefficient == None:
            print("The image of {} doesn't have radiance coefficients".format(basename))
            continue
        ATM_CORRECT(input_ds, out_file, coearr, radiance_coefficient, SatelliteID)
        # 输出大气校正影像的相关信息
        print(basename)
        print(coearr)
        dom = None


if __name__ == '__main__':
    start_time = time.clock()
    file_path = r'\\192.168.0.234\nydsj\user\LXX\烟草2020\GF数据\rpc'
    # ID = ['5896', '5893', '5752']
    out = r"\\192.168.0.234\nydsj\user\LXX\烟草2020\GF数据\atm"
    partfileinfo = 'GF?_*.tiff'
    print('The program starts running!')
    main(file_path, out, partfileinfo)
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
