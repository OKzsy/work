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
    import gdal, ogr, osr

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
    xout = np.arange(num, dtype='float64') * step + wlinf  # 类似于idl中的make_array中使用/index和INCREMENT=step功能
    xout = xout * 1. / 1000
    ori_spec = fun_path + os.sep + '6SV' + os.sep + 'spec' + os.sep + sat_id + '.txt'
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
    Blue_band = np.where(Blue_band == a_nodata, 0, Blue_band)
    Green_band = source_ds.GetRasterBand(2).ReadAsArray()
    Green_band = np.where(Green_band == a_nodata, 0, Green_band)
    Red_band = source_ds.GetRasterBand(3).ReadAsArray()
    Red_band = np.where(Red_band == a_nodata, 0, Red_band)
    Inf_band = source_ds.GetRasterBand(4).ReadAsArray()
    Inf_band = np.where(Inf_band == a_nodata, 0, Inf_band)
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
    Blue_suf_ref = np.where(Blue_suf_ref == Blue_suf_ref.min(), 0.0, Blue_suf_ref)
    Blue_suf_ref = (Blue_suf_ref * 10000).round()
    # Green
    y = atm_coe[1, 0] * Green_ref - atm_coe[1, 1]
    Green_suf_ref = y / (1.0 + atm_coe[1, 2] * y)
    Green_suf_ref = np.where(Green_suf_ref == Green_suf_ref.min(), 0.0, Green_suf_ref)
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
    # 进行重投影和重采样
    new_xs = 0.00004
    new_ys = 0.00004
    dest = reproject_dataset(atm_ds, new_xs, new_ys)
    # 存储经重投影和重采样后的大气校正结果
    print('Store atmospheric correction results after re-projection and re-sampling!')
    driver = gdal.GetDriverByName("GTiff")
    dst_ds = driver.CreateCopy(img_out_path, dest, callback=progress)
    # 释放资源
    atm_ds = None
    dest = None
    dst_ds = None
    source_ds = None
    return None


def main(py_path, file_path, partfileinfo='*AnalyticMS.tif', AOD=0.1696):
    # 注册所有gdal的驱动
    gdal.AllRegister()
    gdal.SetConfigOption("gdal_FILENAME_IS_UTF8", "YES")
    # 获取当前工作路径
    function_position = py_path
    # 需要大气校正影像路径
    original_dir_path = file_path
    original_imgs = searchfiles(original_dir_path, partfileinfo, recursive=True)
    # 定义卫星通道参数，单位微米
    w = [[0.455, 0.515], [0.50, 0.59], [0.59, 0.67], [0.76, 0.86]]
    deg2radian = math.pi / 180.0
    for num_file in range(len(original_imgs)):
        # 开始循环单个文件处理
        input = original_imgs[num_file]
        # 获取文件根目录
        file_dir = os.path.dirname(input)
        # 文件名
        basename = file_basename(input, '.tif')
        # 获取影像元数据路径
        # xml路径
        xmlpath = file_dir + os.sep + basename + '_metadata.xml'
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
        zsat = math.asin(((6371 + 475) / 6371) * math.sin(float(view_angle) * deg2radian)) / deg2radian  # 卫星天顶角
        ID = 'ps:azimuthAngle'
        asat = float(GET_XMLELEMENTS(oDocument, ID))  # 卫星方位角
        ID = 'ps:acquisitionDateTime'
        acqtime = GET_XMLELEMENTS(oDocument, ID)
        month = int(acqtime[5:5 + 2])  # 月份
        day = int(acqtime[8:8 + 2])  # 日期
        if (month >= 4) and (month <= 9):
            idatm = 2  # 大气模式中纬度夏季
        else:
            idatm = 3  # 大气模式中纬度冬季
        iaer = 1  # 气溶胶模式大陆型
        v = 0  # 选择输入能见度还是气溶胶光学厚度
        tao = AOD  # 550nm气溶胶光学厚度
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
        outcoe = function_position + os.sep + '6SV' + os.sep + 'outcoe' + os.sep + imgID + '.txt'
        # 打开辐射校正系数文件用于写入辐射校正系数
        lun_coe = open(outcoe, 'w', newline=None)
        coearr = np.full((4, 3), -999.0, dtype='float16')
        for a in range(4):  # 循环处理各个波段
            band = ['Blue', 'Green', 'Red', 'Ninf']
            txtname = 'in.txt'
            lun = open(txtname, 'w', newline=None)
            lun.write('{:<3d} {} {}'.format(igeom, '(User defined)', '\n'))
            lun.write(
                '{:<10.5f} {:<10.5f} {:<10.5f} {:<10.5f} {:<3d} {:<3d} {} {}'.format(zsun, asun, zsat, asat, month, day,
                                                                                     '(geometrical conditions)', '\n'))
            lun.write('{:<3d} {} {}'.format(idatm, 'Midlatitude Summer', '\n'))
            lun.write('{:<3d} {} {}'.format(iaer, 'Continental Model', '\n'))
            lun.write('{:<3d} {}'.format(v, '\n'))
            lun.write('{:<8.4f} {} {}'.format(tao, 'value', '\n'))
            lun.write('{:<3d} {} {}'.format(xps, '(target level)', '\n'))
            lun.write('{:<3d} {} {}'.format(xpp, '(sensor level)', '\n'))
            lun.write('{:<3d} {} {}'.format(iwave, "User's defined filtered function", '\n'))
            lun.write('{:<7.3} {:<7.3} {}'.format(w[a][0], w[a][1], '\n'))
            res = SECTRUM(w[a][0], w[a][1], a, function_position, sat_id)
            for spec_value in res:
                lun.write('{:<10.6f} {}'.format(spec_value, '\n'))
            lun.write('{:<3d} {} {}'.format(inhomo, 'Homogeneous surface', '\n'))
            lun.write('{:<3d} {} {}'.format(idirect, 'No directional effects', '\n'))
            lun.write('{:<3d} {} {}'.format(igroun, '(mean spectral value)', '\n'))
            lun.write('{:<3d} {} {}'.format(atm, 'Atm. correction Lambertian', '\n'))
            lun.write('{:<5.1f} {} {}'.format(radiance, 'reflectance (negative value)', '\n'))
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
        out_path = file_dir + os.sep + 'outimg'
        if not os.path.isdir(out_path):
            os.makedirs(out_path)
        out_file = out_path + os.sep + out_file_name + '-atm.tif'
        ATM_CORRECT(input, out_file, coearr, oDocument)
        # 输出大气校正影像的相关信息
        print(basename)
        print(coearr)
        dom = None


if __name__ == '__main__':
    start_time = time.clock()
    # file_path = r'\\192.168.0.234\nydsj\user\ZSS\test\planet_order_298137-巩义\planet_order_298137-2'
    # partfileinfo = '*AnalyticMS.tif'
    # # 浮点型的气溶胶光学厚度值
    # tao = 0.5

    print('The program starts running!')
    fun_path = os.path.dirname(sys.argv[0])
    file_path = sys.argv[1]
    partfileinfo = sys.argv[2]
    tao = float(sys.argv[3])

    main(fun_path, file_path, partfileinfo, tao)

    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
