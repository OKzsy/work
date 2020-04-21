#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/3/29 9:30

Description:
    利用gdal.warp接口实现对影像的正射校正

Parameters
    in_file：输入待校正的影像路径
    out_file：输出校正后影像路径
    dem_file：输入DEM影像路径

"""

import os
import sys
import time
import shutil
import psutil

try:
    from osgeo import gdal
except ImportError:
    import gdal, gdalconst
try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def search_file(folder_path, file_extension):
    search_files = []
    for dir_path, dir_names, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(file_extension):
                search_files.append(os.path.normpath(os.path.join(dir_path, file)))
    return search_files


def main(in_file, out_file, dem_file):
    # 单位为字节
    total_memory = psutil.virtual_memory().total

    gdal.SetCacheMax(int(total_memory / 1 * 2))
    #
    tif_driver = gdal.GetDriverByName("GTiff")

    if os.path.exists(out_file):
        tif_driver.Delete(out_file)
    in_xml_file = os.path.splitext(in_file)[0] + '.xml'

    if os.path.exists(in_xml_file):
        gdal.Warp(out_file, in_file, rpc=True, multithread=True, errorThreshold=0.0,
                  resampleAlg=gdal.GRIORA_Bilinear, callback=progress,
                  transformerOptions=['RPC_DEM=%s' % dem_file])

        out_xml_file = os.path.join(os.path.dirname(out_file),
                                    '%s.xml' % os.path.splitext(os.path.basename(out_file))[0])
        shutil.copy(in_xml_file, out_xml_file)

    json_file = search_file(os.path.dirname(in_file), '.json')

    if json_file != []:
        if search_file(os.path.dirname(in_file), '.txt') == []:

            gdal.Warp(out_file, in_file, multithread=True, errorThreshold=0.0,
                      resampleAlg=gdal.GRIORA_Bilinear, callback=progress,
                      transformerOptions=['RPC_DEM=%s' % dem_file])
        else:
            gdal.Warp(out_file, in_file, rpc=True, multithread=True, errorThreshold=0.0,
                      resampleAlg=gdal.GRIORA_Bilinear, callback=progress,
                      transformerOptions=['RPC_DEM=%s' % dem_file])
        out_json_file = os.path.join(os.path.dirname(out_file),
                                     '%s.json' % os.path.splitext(os.path.basename(out_file))[0])
        shutil.copy(json_file[0], out_json_file)


if __name__ == "__main__":
    start_time = time.time()

    #
    # main(in_file, out_file)

    # in_file = r"D:\Data\Test_data\un_zip\out_dir\GF2_PMS2_E114.0_N34.7_20180327_L1A0003087399\GF2_PMS2_E114.0_N34.7_20180327_L1A0003087399-MSS2.tiff"
    # out_file = r"D:\Data\Test_data\un_zip\out_dir\GF2_PMS2_E114.0_N34.7_20180327_L1A0003087399_mss2_ort.tif"
    # dem_file = r"D:\Data\Other_data\dem_zm_8m\gf2_dem.tif"
    #
    in_file = r"\\192.168.0.234\nydsj\user\ZSS\农保项目\1.source\GF1\GF1C_PMS_E114.0_N34.7_20190828_L1A1021464251\GF1C_PMS_E114.0_N34.7_20190828_L1A1021464251-PAN.tiff"
    out_file = r"\\192.168.0.234\nydsj\user\ZSS\农保项目\3.rpc\GF1C_PMS_E114.0_N34.7_20190828_L1A1021464251-PAN.tiff"
    dem_file = r"\\192.168.0.234\nydsj\project\26.玉米分类\1.data\DEM\GF1_2\Level18\GF1_2.tif"
    main(in_file, out_file, dem_file)

    # if len(sys.argv[1:]) < 3:
    #     sys.exit('Problem reading input')
    # main(sys.argv[1], sys.argv[2], sys.argv[3])

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))
