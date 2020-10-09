#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/10/5 15:07
# @Author  : zhaoss
# @FileName: multi_dn2def_red_edge.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import time
import sys
import shutil
import zipfile
import subprocess
import tempfile
import multiprocessing.dummy as mp

from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def un_zip(zip_file, out_dir):
    try:
        zip = zipfile.ZipFile(zip_file, 'r')
        for name in zip.namelist():
            if os.path.exists(os.path.join(out_dir, name)):
                continue
            else:
                zip.extract(name, out_dir)
        zip.close()
    except Exception as e:
        print(e)
        print('Problem opening file %s !' % zip_file)
        return 0


def get_10_jp2(in_list):
    # 10m排序
    jp2_10_list = ['B02_10', 'B03_10', 'B04_10', 'B08_10']

    out_list = []

    for band_pos in jp2_10_list:
        for jp2_file in in_list:
            band_name = os.path.splitext(os.path.basename(jp2_file))[0]

            if band_pos in band_name:
                out_list.append(jp2_file)

    return out_list


def get_20_jp2(in_list):
    # 20m排序
    jp2_20_list = ['B02_20', 'B03_20', 'B04_20', 'B05_20', 'B06_20', 'B07_20', 'B8A_20', 'SCL_20m']

    out_list = []

    for band_pos in jp2_20_list:
        for jp2_file in in_list:
            band_name = os.path.splitext(os.path.basename(jp2_file))[0]

            if band_pos in band_name:
                out_list.append(jp2_file)

    return out_list


def search_file(folder_path, file_extension):
    search_files = []
    for dir_path, dir_names, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(file_extension):
                search_files.append(os.path.normpath(os.path.join(dir_path, file)))
    return search_files


def corner_to_geo(sample, line, dataset):
    """
    :param sample: 列号
    :param line:   行号
    :param dataset: 所在影像的数据集
    :return: 指定行列号的经纬度
    """
    # 计算指定行,列号的地理坐标
    Geo_t = dataset.GetGeoTransform()
    # 计算地理坐标
    geoX = Geo_t[0] + sample * Geo_t[1]
    geoY = Geo_t[3] + line * Geo_t[5]
    return geoX, geoY


def reproject_dataset(src_ds):
    """
    :param src_ds: 待重采样影像的数据集
    :return: 调用ReprojectImage对影像进行重采样，重采样后影像的分辨率为原始影像分辨率，
    投影信息为WGS84。
    """
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
    x_size = src_ds.RasterXSize
    y_size = src_ds.RasterYSize
    bandCount = src_ds.RasterCount
    dataType = src_ds.GetRasterBand(1).DataType
    if oSRC.GetAttrValue("UNIT") == "metre":
        new_x_size = geo_t[1] * 10 ** (-5)
        new_y_size = geo_t[5] * 10 ** (-5)
    else:
        new_x_size = geo_t[1]
        new_y_size = geo_t[5]
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
    dest = mem_drv.Create('', int((lrx - ulx) / new_x_size),
                          int((uly - lry) / -new_y_size), bandCount, dataType)
    # 计算新的放射变换参数
    new_geo = (ulx, new_x_size, geo_t[2], uly, geo_t[4], new_y_size)
    # 为重投影结果设置空间参考
    dest.SetGeoTransform(new_geo)
    dest.SetProjection(oSRS.ExportToWkt())
    # 执行重投影和重采样
    res = gdal.ReprojectImage(src_ds, dest,
                              src_prj, oSRS.ExportToWkt(),
                              gdal.GRA_Bilinear)
    return dest


def dn2ref(out_dir, zip_file):
    # zip所在父目录
    zip_dir = os.path.dirname(zip_file)
    zip_name = os.path.splitext(os.path.basename(zip_file))[0]
    zip_file_name = zip_name
    temp_dir = tempfile.mkdtemp(dir=out_dir, suffix='_un_zip')
    if not os.path.isdir(temp_dir):
        os.mkdir(temp_dir)
    zip_value = un_zip(zip_file, temp_dir)
    if zip_value == 0:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return
    # 增加用于兼容不同网站下载的Sen2数据
    tag = zip_name[0:3]
    if tag == 'L1C':
        zip_name = list(os.walk(temp_dir))[0][1][0][0:-5]
    # 使用Sen2Cor计算地表反射率
    safe_dir = os.path.join(temp_dir, '%s.SAFE' % zip_name)

    if not os.path.isdir(safe_dir):
        sys.exit('No %s.SAFE dir' % zip_name)
    subprocess.call('L2A_Process.bat --refresh %s' % safe_dir)
    # os.system('/home/zhaoshaoshuai/S2/Sen2Cor/bin/L2A_Process --refresh %s' % safe_dir)

    L2_dir_list = list(zip_name.split('_'))
    L2_dir_list[1] = 'MSIL2A'
    L2_dir_name = '_'.join(L2_dir_list)

    L2_dir = os.path.join(temp_dir, '%s.SAFE' % L2_dir_name)
    L2_data_dir = os.path.join(L2_dir, 'GRANULE')

    xml_files = search_file(L2_data_dir, '.xml')

    for xml_file in xml_files:
        xml_dir = os.path.dirname(xml_file)
        jp2_files = search_file(xml_dir, '.jp2')

        if jp2_files == []:
            continue
        xml_name = os.path.basename(xml_dir)

        jp2_10_files = get_10_jp2(jp2_files)
        if jp2_10_files == []:
            continue

        jp2_20_files = get_20_jp2(jp2_files)
        if jp2_20_files == []:
            continue
        # 增加红边波段
        jp2_10_files[3:3] = jp2_20_files[3:7]
        vrt_10_file = os.path.join(safe_dir, '%s_10m.vrt' % xml_name)
        vrt_options = gdal.BuildVRTOptions(resolution='user', xRes=10, yRes=10, separate=True,
                                           resampleAlg='bilinear')
        vrt_10_dataset = gdal.BuildVRT(vrt_10_file, jp2_10_files, options=vrt_options)
        # 重投影
        dst = reproject_dataset(vrt_10_dataset)

        isub_ref_dir = os.path.join(out_dir, zip_file_name)
        if not os.path.isdir(isub_ref_dir):
            os.mkdir(isub_ref_dir)

        out_driver = gdal.GetDriverByName('GTiff')
        out_10_file = os.path.join(isub_ref_dir, '%s_ref_10m.tif' % xml_name)
        print("Start exporting images at 10 meters resolution", flush=True)
        out_10_sds = out_driver.CreateCopy(out_10_file, dst, callback=progress)

        vrt_10_dataset = dest = out_10_sds = None

        shutil.rmtree(temp_dir, ignore_errors=True)


def main(in_dir, out_dir):
    if not os.path.isdir(out_dir):
        os.mkdir(out_dir)

    # 搜索输入路径下所有zip文件
    zip_files = search_file(in_dir, '.zip')

    if zip_files == []:
        sys.exit('no zip file')
    # 建立多个进程
    jobs = os.cpu_count() if os.cpu_count() < len(zip_files) else len(zip_files)
    pool = mp.Pool(processes=jobs)
    for izip in zip_files:
        # dn2ref(out_dir, izip)
        pool.apply_async(dn2ref, args=(out_dir, izip,))
    pool.close()
    pool.join()


if __name__ == '__main__':
    start_time = time.time()

    # if len(sys.argv[1:]) < 2:
    #     sys.exit('Problem reading input')
    #
    # in_dir = sys.argv[1]
    # out_dir = sys.argv[2]
    #
    in_dir = r"\\192.168.0.234\nydsj\user\ZSS\2019qiu\old"
    out_dir = r"\\192.168.0.234\nydsj\user\ZSS\2019qiu\test_out"
    main(in_dir, out_dir)

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))
