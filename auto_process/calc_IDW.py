#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2021/3/16
# @Author  : licheng
Description:
反距离权重法插值算法
in_txt = 已知点txt文件
in_shp = 插值矢量范围（不同于in_txt的空间范围）
tag =  为0时，插值范围按照txt的空间范围来计算，为1时，插值范围按照shp文件的空间范围来计算
out_tif = 输出插值tif的位置(输出结果添加了颜色)

Parameters

"""

import numpy as np
import os
import math
import time
import sys
from math import radians, cos, sin, asin, sqrt
from osgeo import gdal, osr, ogr

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress
colormap = {
    26.7617: [245, 0, 0],
    31.8043: [245, 245, 0],
    37.8684: [0, 245, 0]

}


def haversine(lon1, lat1, lon2, lat2):
    # 计算两个坐标点之间的距离
    R = 6372.8
    dLon = radians(lon2 - lon1)
    dLat = radians(lat2 - lat1)
    lat1 = radians(lat1)
    lat2 = radians(lat2)
    a = sin(dLat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dLon / 2) ** 2
    c = 2 * asin(sqrt(a))
    d = R * c
    return d


def IDW(x, y, z, xi, yi, power_value, points_num):
    # 根据已知的（x,y,z）插值算出坐标点（xi,yi）处的值u，其中xi和yi是一个大小相同（=插值范围）的二维矩阵，xi里存放的是经度，yi里存放的是纬度
    xsize = xi.shape[1]  # xi是矩阵，得到xi的列数
    ysize = xi.shape[0]  # xi是矩阵，得到xi的行数
    lstxyzi = np.zeros((ysize, xsize), dtype=np.float)  # 定义一个大小等于插值范围的0矩阵，并设置float类型
    for iline in range(ysize):
        for irow in range(xsize):
            lstdist = []
            for s in range(len(x)):
                d = haversine(x[s], y[s], xi[iline, irow], yi[iline, irow]) + 0.000001
                lstdist.append(d)
            # 采用边距方式，使用最近的一些点进行插值
            dist = np.array(lstdist)
            acs_index = np.argsort(dist)
            nearest_dist = dist[acs_index][:points_num]
            nearest_z = np.array(z)[acs_index][:points_num]
            sumsup = 1 / np.power(nearest_dist, power_value)
            suminf = np.sum(sumsup)
            sumsup = np.sum(np.array(sumsup) * nearest_z)
            u = sumsup / suminf
            lstxyzi[iline, irow] = u
            # 将某一位置的插值结果输入到对应位置的矩阵中，最终得到的lstxyz是一个包含所有插值结果的矩阵，大小与插值范围相同，也与xi、yi相同
    return lstxyzi


def get_coordinate(im_ds):
    # 读出txt文件里面的每一列的值，并存放于列表中
    with open(im_ds, "r", encoding="utf-8") as f:
        in_data = f.readlines()
        num = len(in_data)
        lat_list = []
        lon_list = []
        soil_list = []
        for i in range(1, num):
            line = in_data[i].split(",")
            lat = float(line[2])
            lon = float(line[3])
            soil = float(line[4])
            lat_list.append(lat)
            lon_list.append(lon)
            soil_list.append(soil)
    return lat_list, lon_list, soil_list


def get_grid(in_ds):
    # 从输入的文件（txt或者shp）中获取数据的四至范围（左上和右下经纬度）
    ds_name = os.path.basename(in_ds)
    if ds_name.endswith(".txt"):
        coor = get_coordinate(in_ds)
        lat_list = coor[0]
        lon_list = coor[1]
        lat_max = max(lat_list)
        lat_min = min(lat_list)
        lon_max = max(lon_list)
        lon_min = min(lon_list)
        in_extent = [(lon_min, lat_max), (lon_max, lat_min)]
    elif ds_name.endswith(".shp"):
        ds = ogr.Open(in_ds)
        if ds is None:
            sys.exit('Could not open {0}.'.format(in_ds))
        in_lyr = ds.GetLayer()
        t = in_lyr.GetExtent()
        in_extent = [(t[0], t[3]), (t[1], t[2])]
    x = math.ceil((in_extent[1][0] - in_extent[0][0]) / 0.0001)
    # 以左上点为原点，0.0001为分辨率（10m），算出沿x正方向（经度逐渐增大）需要的网格列数
    y = math.ceil((in_extent[1][1] - in_extent[0][1]) / -0.0001)
    # 以左上点为原点，0.0001为分辨率（10m），算出沿y负方向（纬度逐渐减小）需要的网格行数
    grid_lon = np.linspace(in_extent[0][0], in_extent[1][0], x)
    grid_lat = np.linspace(in_extent[0][1], in_extent[1][1], y)
    # 以左上点为出发点，按照列数和行数进行等差计算，得到每个网格的经度和纬度值，分别存于一维矩阵向量中
    x_grid, y_grid = np.meshgrid(grid_lon, grid_lat)
    # 将经度的一维矩阵向量和纬度的一维矩阵向量组成两个矩阵网格，大小为y*x，x_grid矩阵用来存放经度，y_grid矩阵用来存放纬度
    return (x_grid, y_grid), in_extent


def main(t1, s1, tag, power_value, needed_points_num, out1):
    coor1 = get_coordinate(t1)
    lat_list1 = coor1[0]
    lon_list1 = coor1[1]
    soil_list1 = coor1[2]
    if tag == 0:
        # 以txt文件数据作为插值范围
        xgrid = get_grid(t1)[0][0]
        ygrid = get_grid(t1)[0][1]
        origin = get_grid(t1)[1][0]
        # origin得到左上角坐标值
    else:
        xgrid = get_grid(s1)[0][0]
        ygrid = get_grid(s1)[0][1]
        origin = get_grid(s1)[1][0]
    pm_idw = IDW(lon_list1, lat_list1, soil_list1, xgrid, ygrid, power_value, needed_points_num)
    # 得到插值结果矩阵
    # 赋予颜色
    xsize = xgrid.shape[1]  # 插值范围列数
    ysize = xgrid.shape[0]  # 插值范围行数
    color = np.zeros((3, ysize, xsize), dtype=np.uint8)
    breakpoints = list(colormap.keys())
    for ichanel in range(3):
        for ibreak in range(len(breakpoints) - 1):
            breakpoint1 = breakpoints[ibreak]
            breakpoint2 = breakpoints[ibreak + 1]
            color1 = colormap[breakpoint1][ichanel]
            color2 = colormap[breakpoint2][ichanel]
            # 创建拉伸方程
            temp_index = np.where((pm_idw >= breakpoint1) & (pm_idw < breakpoint2))
            color[ichanel, temp_index[0], temp_index[1]] = (
                    (pm_idw[temp_index] - breakpoint1) * (color2 - color1) / (
                    breakpoint2 - breakpoint1) + color1).astype(np.uint8)
    # 写入栅格
    tiff_driver = gdal.GetDriverByName('GTiff')
    out_name = "idw_color_{}_{}.tif".format(power_value, needed_points_num)
    out_tif1 = os.path.join(out1, out_name)
    # out_ds = tiff_driver.Create(out_tif1, xsize, ysize, 3, gdal.GDT_Byte)  # 新建一个栅格对象
    out_ds = tiff_driver.Create(out_tif1, xsize, ysize, 1, gdal.GDT_Float32)  # 新建一个栅格对象
    geo_wgs84 = osr.SpatialReference()
    geo_wgs84.ImportFromEPSG(4326)
    out_ds.SetProjection(geo_wgs84.ExportToWkt())
    # 设置wgs84投影坐标系
    out_ds.SetGeoTransform((origin[0], 0.0001, 0.0, origin[1], 0.0, -0.0001))
    # 设定左上角坐标、分辨率和旋转角度 （注意：由于左上角纬度向下是递减所以分辨率为-0.0001）
    out_ds.GetRasterBand(1).WriteArray(pm_idw)
    # for iband in range(3):
    #     band = out_ds.GetRasterBand(iband + 1)
    #     band.WriteArray(color[iband, :, :])
    #     band.FlushCache()
    out_ds = None
    # 关闭数据集


if __name__ == '__main__':
    gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
    start_time = time.time()
    in_txt = r"F:\test\idw\new.txt"
    in_shp = r"\\192.168.0.234\nydsj\project\40.长垣高标准农田\2.vector\2.人工勾画\耕地合并.shp"
    tag = 0
    # p_value = 2
    # needed_points_num = 5
    out_tif = r"F:\test\idw"
    # for p_value in range(2, 10):
    p_value = 0.125
    for needed_points_num in range(-1, 12):
        main(in_txt, in_shp, tag, p_value, needed_points_num, out_tif)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
