#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/7/19 10:05


Description:
    利用多进程，批量对Sentinel-2原始数据进行解压、大气校正等处理，生成10m、20m和分类数据

Parameters
    参数1:原始文件存放目录
    参数2:地表反射率输出目录

"""

import os
import time
import sys
import shutil
import zipfile
import subprocess
from functools import partial
import multiprocessing.dummy as mp
from threading import Thread

try:
    from osgeo import gdal
except ImportError:
    import gdal

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def un_zip(zip_file, out_dir):
    try:
        with zipfile.ZipFile(zip_file, 'r') as zip:
            for file in zip.filelist:
                # print(file.filename)
                if os.path.exists(os.path.join(out_dir, file.filename)):
                    # print('no')
                    continue
                else:
                    # print('yes')
                    zip.extract(file, out_dir)
                # zip.extractall(out_dir)
    except:
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


def reproj_resample(in_file, match_file, out_file):
    source_dataset = gdal.Open(in_file)
    if source_dataset is None:
        sys.exit('Problem opening file %s !' % in_file)

    # 获取数据基本信息
    num_band = source_dataset.RasterCount
    data_type = source_dataset.GetRasterBand(1).DataType
    in_proj = source_dataset.GetProjectionRef()

    match_dataset = gdal.Open(match_file)
    match_proj = match_dataset.GetProjection()
    match_geo = match_dataset.GetGeoTransform()
    out_xsize = match_dataset.RasterXSize
    out_ysize = match_dataset.RasterYSize

    driver = gdal.GetDriverByName('GTiff')
    out_dataset = driver.Create(out_file, out_xsize, out_ysize, num_band, data_type)
    out_dataset.SetGeoTransform(match_geo)
    out_dataset.SetProjection(match_proj)

    for i in range(num_band):

        band = source_dataset.GetRasterBand(i + 1)

        if band.GetNoDataValue() is None:
            no_data = 0
        else:
            no_data = band.GetNoDataValue()
        out_band = out_dataset.GetRasterBand(i + 1)
        out_band.SetNoDataValue(no_data)

    gdal.ReprojectImage(source_dataset, out_dataset, in_proj, match_proj, gdal.GRA_Bilinear)

    source_dataset = None
    out_dataset = None


def dn2ref(out_dir, zip_file):
    # zip所在父目录
    zip_dir = os.path.dirname(zip_file)
    zip_name = os.path.splitext(os.path.basename(zip_file))[0]
    zip_file_name = zip_name
    temp_dir = os.path.normpath(os.path.join(out_dir, zip_name + '_un_zip'))
    if not os.path.isdir(temp_dir):
        os.mkdir(temp_dir)

    zip_value = un_zip(zip_file, temp_dir)
    if zip_value is None:
        return
    if zip_value == 0:
        shutil.rmtree(temp_dir)
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

        # 近红外波段重采样
        # resam_nir_name_list = list(os.path.splitext(os.path.basename(jp2_20_files[0]))[0].split('_'))
        # resam_nir_name_list[2] = 'B08'
        # resam_nir_file = os.path.join(os.path.dirname(jp2_20_files[0]), '%s.jp2' % '_'.join(resam_nir_name_list))
        # reproj_resample(jp2_10_files[-1], jp2_20_files[0], resam_nir_file)

        # jp2_20_files.insert(-3, jp2_10_files[-1])

        vrt_10_file = os.path.join(safe_dir, '%s_10m.vrt' % xml_name)
        vrt_20_file = os.path.join(safe_dir, '%s_20m.vrt' % xml_name)
        vrt_10_dataset = gdal.BuildVRT(vrt_10_file, jp2_10_files, separate=True)
        vrt_20_dataset = gdal.BuildVRT(vrt_20_file, jp2_20_files[:-1], resolution='user', xRes=20, yRes=20,
                                       separate=True,
                                       options=['-r', 'bilinear'])
        vrt_10_dataset.FlushCache()
        vrt_20_dataset.FlushCache()
        vrt_10_dataset = None
        vrt_20_dataset = None

        isub_ref_dir = os.path.join(out_dir, zip_file_name)
        if not os.path.isdir(isub_ref_dir):
            os.mkdir(isub_ref_dir)

        out_driver = gdal.GetDriverByName('GTiff')
        out_10_file = os.path.join(isub_ref_dir, '%s_ref_10m.tif' % xml_name)
        out_20_file = os.path.join(isub_ref_dir, '%s_ref_20m.tif' % xml_name)
        class_file = os.path.join(isub_ref_dir, '%s_SCL_20m.tif' % xml_name)
        print("Start exporting images at 10 meters resolution")
        out_10_sds = out_driver.CreateCopy(out_10_file, gdal.Open(vrt_10_file), callback=progress)
        print("Start exporting images at 20 meters resolution")
        out_20_sds = out_driver.CreateCopy(out_20_file, gdal.Open(vrt_20_file), callback=progress)
        out_class_sds = out_driver.CreateCopy(class_file, gdal.Open(jp2_20_files[-1]), callback=progress)

        out_10_sds = None
        out_20_sds = None
        out_class_sds = None

        shutil.rmtree(temp_dir)


def main(in_dir, out_dir):
    if not os.path.isdir(out_dir):
        os.mkdir(out_dir)

    # 搜索输入路径下所有zip文件
    zip_files = search_file(in_dir, '.zip')

    if zip_files == []:
        sys.exit('no zip file')
    # 建立多个进程
    # pool = mp.Pool(processes=4)
    # func = partial(dn2ref, out_dir)
    # for izip in zip_files:
    #     res = pool.apply_async(func, args=(izip,))
    # pool.close()
    # pool.join()
    # 建立多个进程
    num_proc = 4
    for zip in range(0, len(zip_files), num_proc):

        sub_zip_list = zip_files[zip: num_proc + zip]

        thread_list = []
        for izip in sub_zip_list:
            # dn2ref(out_dir, izip)
            thread = Thread(target=dn2ref, args=(out_dir, izip,))
            thread.start()
            thread_list.append(thread)

        for it in thread_list:
            it.join()


if __name__ == '__main__':
    start_time = time.time()

    # if len(sys.argv[1:]) < 2:
    #     sys.exit('Problem reading input')
    #
    # in_dir = sys.argv[1]
    # out_dir = sys.argv[2]
    #
    in_dir = r"\\192.168.0.234\nydsj\user\ZSS\zhengzhou_s2\T49SFU"
    out_dir = r"\\192.168.0.234\nydsj\user\ZSS\zhengzhou_s2\out_T49SKD"
    main(in_dir, out_dir)

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))
