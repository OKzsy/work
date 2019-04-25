#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/12/27 15:19

Description:
    

Parameters
    

"""

import os
import sys
import time
import random
import string
import tempfile
import shutil
import psutil
import numpy as np
import multiprocessing as mp

try:
    from osgeo import gdal, ogr, osr
except ImportError:
    import gdal, ogr, osr

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress

def search_file(folder_path, file_extension):
    search_files = []
    for dirpath, dirnames, files in os.walk(folder_path):
        for file in files:
            if (file.lower().endswith(file_extension)):
                search_files.append(os.path.normpath(os.path.join(dirpath, file)))
    return search_files

# 文件直角坐标转成文件地理坐标
def to_geo(fileX, fileY, file_geo):
    geoX = file_geo[0] + fileX * file_geo[1]
    geoY = file_geo[3] + fileY * file_geo[5]
    return geoX, geoY

def reproj(in_list):

    in_files = in_list[0]
    out_dir = in_list[1]

    for ifile in range(len(in_files)):

        # 原始影像左上角坐标有误，需要调整
        ori_dir = os.path.join(out_dir, 'ori')
        if not os.path.exists(ori_dir):
            os.mkdir(ori_dir)

        re_proj = os.path.join(out_dir, 'reproj')
        if not os.path.exists(re_proj):
            os.mkdir(re_proj)
        ori_file = os.path.join(ori_dir, '%s_ori.tif' %
                                os.path.splitext(os.path.basename(in_files[ifile]))[0])

        reproj_file = os.path.join(re_proj, '%s_reproj.tif' %
                                os.path.splitext(os.path.basename(in_files[ifile]))[0])

        if (os.path.exists(ori_file)) and (os.path.exists(reproj_file)):
            continue

        source_dataset = gdal.Open(in_files[ifile])
        if source_dataset is None:
            sys.exit('Problem opening file %s !' % in_files[ifile])

        # 获取数据基本信息
        xsize = source_dataset.RasterXSize
        ysize = source_dataset.RasterYSize
        num_band = source_dataset.RasterCount
        data_type = source_dataset.GetRasterBand(1).DataType

        in_geo = source_dataset.GetGeoTransform()
        # in_proj = source_dataset.GetProjectionRef()


        # 建立缓存文件
        out_driver = gdal.GetDriverByName('GTiff')
        out_dataset = out_driver.CreateCopy(ori_file, source_dataset)
        in_geotran = (in_geo[0] / 100.0, in_geo[1], in_geo[2], in_geo[3], in_geo[4], in_geo[5])

        in_proj = 'PROJCS["CGCS2000_3_Degree_GK_CM_114E",' \
                  'GEOGCS["GCS_China_Geodetic_Coordinate_System_2000",' \
                  'DATUM["D_China_2000",SPHEROID["CGCS2000",6378137.0,298.257222101]],' \
                  'PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],' \
                  'PARAMETER["False_Easting",500000.0],PARAMETER["False_Northing",0.0],' \
                  'PARAMETER["Central_Meridian",114.0],PARAMETER["Scale_Factor",1.0],' \
                  'PARAMETER["Latitude_Of_Origin",0.0],UNIT["Meter",1.0]]'

        out_dataset.SetGeoTransform(in_geotran)
        out_dataset.SetProjection(in_proj)

        source_dataset = None
        out_dataset = None

        # 获取数据基本信息

        in_proj_wkt = osr.SpatialReference()
        in_proj_wkt.ImportFromWkt(in_proj)


        out_proj_wkt = osr.SpatialReference()
        out_proj_wkt.ImportFromEPSG(3857)


        gdal.Warp(reproj_file, ori_file, format='GTiff',
                  srcSRS=in_proj, dstSRS=out_proj_wkt.ExportToWkt(),
                  srcNodata=0, dstNodata=0, multithread=True, xRes=abs(in_geo[1]),
                  yRes=abs(in_geo[5]))

        progress((ifile+1) / len(in_files))



def main(in_dir, out_dir):


    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    tif_files = search_file(in_dir, '.tif')
    if tif_files == []:
        sys.exit('no file')

    num_proc = int(mp.cpu_count() - 1)
    if len(tif_files) < num_proc:
        num_proc = len(tif_files)
        block_num_file = 1
    else:
        block_num_file = int(len(tif_files) / num_proc)


    r_list = []  # 进程返回结果
    pool = mp.Pool(processes=num_proc)

    for iproc in range(num_proc):

        if iproc == (num_proc - 1):
            sub_in_files = tif_files[(iproc * block_num_file):]
        else:
            sub_in_files = tif_files[(iproc * block_num_file): (iproc * block_num_file) + block_num_file]

        in_list = [sub_in_files, out_dir]

        r_list.append(pool.apply_async(reproj, args=(in_list,)))

    pool.close()
    pool.join()

    for r in r_list:
        r_get_data = r.get()


if __name__ == '__main__':
    start_time = time.time()

    # in_file = r"\\192.168.0.234\nydsj\user\ZSS\test\aaa\Level18\I49H062160_2000.tif"
    # out_file = r"\\192.168.0.234\nydsj\user\ZSS\test\aaa\Level18\I49H062160_2000_reproj.tif"



    # if len(sys.argv[1:]) < 2:
    #     sys.exit('Problem reading input')
    #
    # in_dir = sys.argv[1]
    # out_dir = sys.argv[2]

    in_dir = r'\\192.168.0.234\nydsj\user\TJG\projection'
    out_dir = r"\\192.168.0.234\nydsj\user\TJG\projection_out"



    main(in_dir, out_dir)

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))