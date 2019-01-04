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
import multiprocessing as mp
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

def rpc_orth(in_list):
    in_files = in_list[:-2]
    dem_file = in_list[-2]
    out_dir = in_list[-1]

    # 单位为字节
    total_memory = psutil.virtual_memory().total

    gdal.SetCacheMax(int(total_memory / 1 * 2))
    #
    tif_driver = gdal.GetDriverByName("GTiff")

    for in_file in in_files:

        input_name = os.path.splitext(os.path.basename(in_file))[0]

        out_file = os.path.join(out_dir, '%s.tif' %input_name)

        if os.path.exists(out_file):
            tif_driver.Delete(out_file)

        in_xml_file = os.path.splitext(in_file)[0] + '.xml'

        if os.path.exists(in_xml_file):
            gdal.Warp(out_file, in_file, rpc=True, multithread=True, errorThreshold=0.0,
                      resampleAlg=gdal.GRIORA_Bilinear,
                      transformerOptions=['RPC_DEM=%s' % dem_file])

            out_xml_file = os.path.join(os.path.dirname(out_file),
                                        '%s.xml' % os.path.splitext(os.path.basename(out_file))[0])
            shutil.copy(in_xml_file, out_xml_file)

        json_file = search_file(os.path.dirname(in_file), '.json')

        if json_file != []:
            if search_file(os.path.dirname(in_file), '.txt') == []:

                gdal.Warp(out_file, in_file, multithread=True, errorThreshold=0.0,
                          resampleAlg=gdal.GRIORA_Bilinear,
                          transformerOptions=['RPC_DEM=%s' % dem_file])
            else:
                gdal.Warp(out_file, in_file, rpc=True, multithread=True, errorThreshold=0.0,
                          resampleAlg=gdal.GRIORA_Bilinear,
                          transformerOptions=['RPC_DEM=%s' % dem_file])
            out_json_file = os.path.join(os.path.dirname(out_file),
                                         '%s.json' % os.path.splitext(os.path.basename(out_file))[0])
            shutil.copy(json_file[0], out_json_file)


def main(in_dir, dem_file, out_dir):
    # 新建
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.mkdir(out_dir)

    input_tiff_files = search_file(in_dir, '.tiff')
    input_tif_files = search_file(in_dir, '.tif')

    input_files = input_tif_files + input_tiff_files

    if input_files == []:
        sys.exit('no files')

    num_proc = int(mp.cpu_count() * 1 / 2)
    pool = mp.Pool(processes=num_proc)

    block_num_file = int(len(input_files) / num_proc)

    for iproc in range(num_proc):

        if iproc == (num_proc - 1):
            sub_in_files = input_files[(iproc * block_num_file):]
        else:
            sub_in_files = input_files[(iproc * block_num_file): (iproc * block_num_file) + block_num_file]

        in_list = sub_in_files + [dem_file, out_dir]

        pool.apply_async(rpc_orth, args=(in_list,))

        progress(iproc / num_proc)
    pool.close()
    pool.join()


if __name__ == "__main__":

    start_time = time.time()

    #
    in_dir = r"D:\Data\RS_data\GF\luoshanxian_unzip"
    out_dir = r"D:\Data\RS_data\GF\luoshanxian_unzip_rpc"
    dem_file = r"C:\Program Files\Exelis\ENVI53\data\GMTED2010.jp2"
    # dem_file = r'C:\Program Files\Exelis\ENVI53\data\GMTED2010.jp2'
    main(in_dir, dem_file, out_dir)

    # if len(sys.argv[1:]) < 3:
    #     sys.exit('Problem reading input')
    # main(sys.argv[1], sys.argv[2], sys.argv[3])

    end_time = time.time()
    print( "time: %.2f min." % ((end_time - start_time) / 60))