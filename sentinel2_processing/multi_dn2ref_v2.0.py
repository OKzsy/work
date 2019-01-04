#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/8/20 17:34

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
import multiprocessing as mp

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


def dn2ref(in_list):


    zip_files = in_list[0]
    out_dir = in_list[1]

    for zip_file in zip_files:

        # zip所在父目录
        zip_name = os.path.splitext(os.path.basename(zip_file))[0]

        temp_dir = os.path.normpath(os.path.join(out_dir, zip_name))
        if not os.path.isdir(temp_dir):
            os.mkdir(temp_dir)

        zip_value = un_zip(zip_file, temp_dir)

        #
        if zip_value == 0:
            shutil.rmtree(temp_dir)
            continue

        # 使用Sen2Cor计算地表反射率
        safe_dir = os.path.join(temp_dir, '%s.SAFE' % zip_name)

        if not os.path.isdir(safe_dir):
            sys.exit('No %s.SAFE dir' % zip_name)
        subprocess.call('L2A_Process.bat --refresh %s' % safe_dir)


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

            jp2_20_files.insert(-3, jp2_10_files[-1])

            vrt_10_file = os.path.join(safe_dir, '%s_10m.vrt' % xml_name)
            vrt_20_file = os.path.join(safe_dir, '%s_20m.vrt' % xml_name)
            gdal.BuildVRT(vrt_10_file, jp2_10_files, separate=True)
            gdal.BuildVRT(vrt_20_file, jp2_20_files[:-1], resolution='user', xRes=20, yRes=20, separate=True,
                          options=['-r', 'bilinear'])

            all_ref_dir = os.path.join(out_dir, 'All_ref')
            if not os.path.isdir(all_ref_dir):
                os.mkdir(all_ref_dir)

            sub_ref_dir = os.path.join(out_dir, 'Sub_ref')
            if not os.path.isdir(sub_ref_dir):
                os.mkdir(sub_ref_dir)

            isub_ref_dir = os.path.join(sub_ref_dir, L2_dir_name)
            if not os.path.isdir(isub_ref_dir):
                os.mkdir(isub_ref_dir)

            out_driver = gdal.GetDriverByName('GTiff')
            out_10_file = os.path.join(isub_ref_dir, '%s_ref_10m.tif' % xml_name)
            out_20_file = os.path.join(isub_ref_dir, '%s_ref_20m.tif' % xml_name)
            class_file = os.path.join(isub_ref_dir, '%s_SCL_20m.tif' % xml_name)

            out_10_sds = out_driver.CreateCopy(out_10_file, gdal.Open(vrt_10_file))
            out_20_sds = out_driver.CreateCopy(out_20_file, gdal.Open(vrt_20_file))
            out_class_sds = out_driver.CreateCopy(class_file, gdal.Open(jp2_20_files[-1]))

            out_10_sds = None
            out_20_sds = None
            out_class_sds = None

            # os.rename(jp2_20_files[-1], class_file)

            if os.path.isdir(os.path.join(all_ref_dir, '%s.SAFE' % L2_dir_name)):
                shutil.rmtree(os.path.join(all_ref_dir, '%s.SAFE' % L2_dir_name))

            shutil.move(L2_dir, all_ref_dir)

            shutil.rmtree(temp_dir)


def main(in_dir, out_dir):

    if not os.path.isdir(out_dir):
        os.mkdir(out_dir)

    # 搜索输入路径下所有zip文件
    zip_files = search_file(in_dir, '.zip')

    if zip_files == []:
        sys.exit('no zip file')

    # 可以修改进程数
    # 单进程
    # in_list = [zip_files, out_dir]
    # dn2ref(in_list,)
    num_proc = int(mp.cpu_count() * 1 / 2)
    num_proc = 4
    if len(zip_files) < num_proc:
        num_proc = len(zip_files)
        block_num_file = 1
    else:
        block_num_file = int(len(zip_files) / num_proc)

    #
    pool = mp.Pool(processes=num_proc)


    for iproc in range(num_proc):

        if iproc == (num_proc - 1):
            sub_in_files = zip_files[(iproc * block_num_file):]
        else:
            sub_in_files = zip_files[(iproc * block_num_file): (iproc * block_num_file) + block_num_file]

        in_list = [sub_in_files, out_dir]

        pool.apply_async(dn2ref, args=(in_list, ))

        # progress(iproc / num_proc)
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
    # in_dir = r"C:\Users\01\Desktop\zhumadian_S2"
    # out_dir = r"outzhumadian"

    in_dir = r"C:\Users\01\Desktop\zhumadian_S2"
    out_dir = r"C:\Users\01\Desktop\outzhumadian"
    main(in_dir, out_dir)

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))