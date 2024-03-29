#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Author: zhaoss
Email:zhaoshaoshuai@hnnydsj.com
Create date: 2019/01/10

Description:
    Atmospheric correction of images

Parameters
    file_path: Image directory
    partfileinfo: Use regular expressions to select images to process,The default is '*AnalyticMS.tif'
    tao: the aerosol optical depth

"""
import os
import sys
import glob
import fnmatch
import math
import xml.dom.minidom
import numpy as np
import time
from scipy import interpolate

try:
    from osgeo import gdal, ogr, osr
except ImportError:
    import gdal
    import ogr
    import osr

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


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
        elif fnmatch.fnmatch(mpath, partfileinfo):
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


def SECTRUM(wlinf, wlsup, band, fun_path, sat_id):
    # 对光谱进行插值
    wlinf = wlinf * 1000
    wlsup = wlsup * 1000
    step = 2.5
    num = math.ceil((wlsup - wlinf) * 1. / step) + 1
    # 类似于idl中的make_array中使用/index和INCREMENT=step功能
    xout = np.arange(num, dtype='float64') * step + wlinf
    xout = xout * 1. / 1000
    ori_spec = fun_path + os.sep + '6SV' + \
               os.sep + 'spec' + os.sep + sat_id + '.txt'
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


def ATM_CORRECT(img_in_path, img_out_path, atm_coe, oDocument):
    # 对影像进行大气校正
    # 原影像路径
    file_inpath = img_in_path
    # 影像输出路径
    file_outpath = img_out_path
    basename = file_basename(file_inpath)
    # Planet定标系数
    ID = 'ps:radiometricScaleFactor'
    ref_coe = np.array(GET_XMLELEMENTS(oDocument, ID), dtype='float16')
    # 大气校正系数
    # xa, xb, xc
    # y = xa * (measured radiance) - xb
    # acr = y / (1. + xc * y)
    # atm_coe = ['Blue', 'Green', 'Red', 'Ninf']
    # 打开影像
    source_ds = gdal.Open(file_inpath)
    # 获取投影和放射变换参数
    source_prj = source_ds.GetProjection()
    source_geo = source_ds.GetGeoTransform()
    # 获取影像的NoData值
    source_in_band = source_ds.GetRasterBand(1)
    a_nodata = source_in_band.GetNoDataValue()
    # 获取数据
    Blue_band = source_ds.GetRasterBand(1).ReadAsArray()
    Blue_band = np.where(Blue_band == abs(a_nodata), 0, Blue_band)
    Green_band = source_ds.GetRasterBand(2).ReadAsArray()
    Green_band = np.where(Green_band == abs(a_nodata), 0, Green_band)
    Red_band = source_ds.GetRasterBand(3).ReadAsArray()
    Red_band = np.where(Red_band == abs(a_nodata), 0, Red_band)
    Inf_band = source_ds.GetRasterBand(4).ReadAsArray()
    Inf_band = np.where(Inf_band == abs(a_nodata), 0, Inf_band)
    # 判断是否缺少波段
    if Blue_band.max() == 0 or Green_band.max() == 0 or Red_band.max() == 0 or Inf_band.max() == 0:
        print('The {} file has no inf band'.format('basename'))
        return
    # 辐射定标至表观反射率
    Blue_ref = Blue_band * ref_coe[0]
    Green_ref = Green_band * ref_coe[1]
    Red_ref = Red_band * ref_coe[2]
    Inf_ref = Inf_band * ref_coe[3]
    # 大气校正
    # Blue
    y = atm_coe[0, 0] * Blue_ref - atm_coe[0, 1]
    Blue_suf_ref = y / (1.0 + atm_coe[0, 2] * y)
    Blue_suf_ref = np.where(
        Blue_suf_ref == Blue_suf_ref.min(), 0.0, Blue_suf_ref)
    Blue_suf_ref = (Blue_suf_ref * 10000).round()
    # Green
    y = atm_coe[1, 0] * Green_ref - atm_coe[1, 1]
    Green_suf_ref = y / (1.0 + atm_coe[1, 2] * y)
    Green_suf_ref = np.where(
        Green_suf_ref == Green_suf_ref.min(), 0.0, Green_suf_ref)
    Green_suf_ref = (Green_suf_ref * 10000).round()
    # Red
    y = atm_coe[2, 0] * Red_ref - atm_coe[2, 1]
    Red_suf_ref = y / (1.0 + atm_coe[2, 2] * y)
    Red_suf_ref = np.where(Red_suf_ref == Red_suf_ref.min(), 0.0, Red_suf_ref)
    Red_suf_ref = (Red_suf_ref * 10000).round()
    # Inf
    y = atm_coe[3, 0] * Inf_ref - atm_coe[3, 1]
    Inf_suf_ref = y / (1.0 + atm_coe[3, 2] * y)
    Inf_suf_ref = np.where(Inf_suf_ref == Inf_suf_ref.min(), 0.0, Inf_suf_ref)
    Inf_suf_ref = (Inf_suf_ref * 10000).round()
    # 创建临时数据集用于存放大气校正结果
    print('Temporary storage of original atmospheric calibration results!')
    tmp_driver = gdal.GetDriverByName('MEM')
    atm_ds = tmp_driver.CreateCopy("", source_ds, callback=progress)
    atm_ds.GetRasterBand(1).WriteArray(Blue_suf_ref)
    atm_ds.GetRasterBand(2).WriteArray(Green_suf_ref)
    atm_ds.GetRasterBand(3).WriteArray(Red_suf_ref)
    atm_ds.GetRasterBand(4).WriteArray(Inf_suf_ref)
    # 存储经重投影和重采样后的大气校正结果
    print('Store atmospheric correction results !')
    driver = gdal.GetDriverByName("GTiff")
    dst_ds = driver.CreateCopy(img_out_path, atm_ds, callback=progress)
    # 释放资源
    atm_ds = None
    dst_ds = None
    source_ds = None
    return None


def get_aod(oDocument, aod_file):
    aod_ds = gdal.Open(aod_file)
    aod_geo = aod_ds.GetGeoTransform()
    aod_inv_geo = gdal.InvGeoTransform(aod_geo)
    # 左上经度
    ID = 'ps:longitude'
    ulx = float(GET_XMLELEMENTS(oDocument, ID)[0])
    # 左上纬度
    ID = 'ps:latitude'
    uly = float(GET_XMLELEMENTS(oDocument, ID)[0])
    # 右下经度
    ID = 'ps:longitude'
    lrx = float(GET_XMLELEMENTS(oDocument, ID)[2])
    # 右下纬度
    ID = 'ps:latitude'
    lry = float(GET_XMLELEMENTS(oDocument, ID)[2])
    extent = [ulx, uly, lrx, lry]
    # 计算在aod影像上的行列号
    off_ulx, off_uly = map(int, gdal.ApplyGeoTransform(
        aod_inv_geo, extent[0], extent[1]))
    off_drx, off_dry = map(math.ceil, gdal.ApplyGeoTransform(
        aod_inv_geo, extent[2], extent[3]))
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


def run_6s(file_path, out_path, partfileinfo='*AnalyticMS.tif'):
    # 获取当前工作路径
    function_position = os.path.dirname(os.path.abspath(sys.argv[0]))
    # 需要大气校正影像路径
    original_dir_path = file_path
    original_imgs = searchfiles(
        original_dir_path, partfileinfo, recursive=True)
    # 定义卫星通道参数，单位微米
    w = [[0.455, 0.515], [0.50, 0.59], [0.59, 0.67], [0.76, 0.86]]
    deg2radian = math.pi / 180.0
    for num_file in range(len(original_imgs)):
        # 开始循环单个文件处理
        input = original_imgs[num_file]
        # 获取文件根目录
        file_dir = os.path.dirname(input)
        # 文件名
        basename = os.path.splitext(os.path.basename(input))[0]
        # 获取影像元数据路径
        # xml路径
        xmlpath = os.path.join(file_dir, basename) + '_metadata.xml'
        if not os.path.exists(xmlpath):
            print('The file: {0} has no xml!'.format(input))
            continue
        # 打开xml文件
        oDocument = xml.dom.minidom.parse(xmlpath).documentElement
        ID = 'eop:serialIdentifier'  # 卫星id
        sat_id = GET_XMLELEMENTS(oDocument, ID)
        sat_id = sat_id[0:2]
        ID = 'eop:identifier'
        imgID = GET_XMLELEMENTS(oDocument, ID)
        igeom = 0  # 自定义几何条件
        ID = 'opt:illuminationElevationAngle'
        zsun = GET_XMLELEMENTS(oDocument, ID)
        zsun = 90.0 - float(zsun)  # 太阳天顶角
        ID = 'opt:illuminationAzimuthAngle'
        asun = float(GET_XMLELEMENTS(oDocument, ID))  # 太阳方位角
        ID = 'ps:spaceCraftViewAngle'
        view_angle = GET_XMLELEMENTS(oDocument, ID)
        zsat = math.asin(((6371 + 475) / 6371) *
                         math.sin(float(view_angle) * deg2radian)) / deg2radian  # 卫星天顶角
        ID = 'ps:azimuthAngle'
        asat = float(GET_XMLELEMENTS(oDocument, ID))  # 卫星方位角
        ID = 'ps:acquisitionDateTime'
        acqtime = GET_XMLELEMENTS(oDocument, ID)
        year = acqtime[0:4]  # 年份
        month = acqtime[5:5 + 2]  # 月份
        day = acqtime[8:8 + 2]  # 日期
        if (int(month) >= 4) and (int(month) <= 9):
            idatm = 2  # 大气模式中纬度夏季
        else:
            idatm = 3  # 大气模式中纬度冬季
        iaer = 1  # 气溶胶模式大陆型
        v = 0  # 选择输入能见度还是气溶胶光学厚度
        # 组合对应aod文件名字
        aod_path = os.path.join(function_position, '6SV', 'tif_aod')
        basename_aod = year + month + day + '.tif'
        aod_file = os.path.join(aod_path, basename_aod)
        # 获取AOD
        tao = round(get_aod(oDocument, aod_file), 3)  # 550nm气溶胶光学厚度
        print('AOD:{}'.format(tao))
        xps = 0  # 目标物高度
        xpp = -475  # 星测
        iwave = 1  # 自定义1输入波段范围和反射相函数
        inhomo = 0  # 地表反射率均一地表
        idirect = 0  # 无方向效应
        igroun = 1  # 绿色植被
        atm = 0  # Atm.correction Lambertian
        radiance = -0.5  # radiance(positivevalue)
        # 更改程序工作路径
        os.chdir(function_position + os.sep + '6SV')
        # 输出辐射校正系数
        outcoe = function_position + os.sep + '6SV' + \
                 os.sep + 'outcoe' + os.sep + imgID + '.txt'
        # 打开辐射校正系数文件用于写入辐射校正系数
        lun_coe = open(outcoe, 'w', newline=None)
        coearr = np.full((4, 3), -999.0, dtype='float16')
        for a in range(4):  # 循环处理各个波段
            band = ['Blue', 'Green', 'Red', 'Ninf']
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
            lun.write('{:<3d} {} {}'.format(
                iwave, "User's defined filtered function", '\n'))
            lun.write('{:<7.3} {:<7.3} {}'.format(w[a][0], w[a][1], '\n'))
            res = SECTRUM(w[a][0], w[a][1], a, function_position, sat_id)
            for spec_value in res:
                lun.write('{:<10.6f} {}'.format(spec_value, '\n'))
            lun.write('{:<3d} {} {}'.format(
                inhomo, 'Homogeneous surface', '\n'))
            lun.write('{:<3d} {} {}'.format(
                idirect, 'No directional effects', '\n'))
            lun.write('{:<3d} {} {}'.format(
                igroun, '(mean spectral value)', '\n'))
            lun.write('{:<3d} {} {}'.format(
                atm, 'Atm. correction Lambertian', '\n'))
            lun.write('{:<5.1f} {} {}'.format(
                radiance, 'reflectance (negative value)', '\n'))
            # 关闭参数输入文件
            lun.close()
            os.system('6sv1-run.exe<in.txt>out.txt')
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
        out_file = os.path.join(out_path, out_file_name) + '-atm.tif'
        ATM_CORRECT(input, out_file, coearr, oDocument)
        # 输出大气校正影像的相关信息
        print(basename)
        print(coearr)
        dom = None
    return 0


def main(**Keywords):
    # 注册所有gdal的驱动
    gdal.AllRegister()
    gdal.SetConfigOption("gdal_FILENAME_IS_UTF8", "YES")
    # 获取参数
    file_path = Keywords['file_path']
    out_path = Keywords['out']
    partfileinfo = Keywords['partfileinfo']
    # 开始进行大气校正
    result = run_6s(file_path, out_path, partfileinfo)


if __name__ == '__main__':
    start_time = time.clock()
    file_path = r'G:\sample_data\planet\planet_order_275915_queshan\20180614_023503_103e'
    out = r"G:\sample_data\planet\planet_order_275915_queshan\out"
    partfileinfo = '*AnalyticMS.tif'
    print('The program starts running!')
    main(file_path=file_path, out=out, partfileinfo=partfileinfo)

    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
