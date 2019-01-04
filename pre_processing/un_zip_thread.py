#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/6/27 14:18

Description:
    对后缀为.gz和.zip的压缩文件包进行多进程解压处理

Parameters
   in_dir:压缩包所在文件夹
   out_dir:解压输出文件夹

"""

import os
import sys
import time
import zipfile
import tarfile
import gzip
from threading import Thread
import multiprocessing

try:
    from osgeo import gdal
except ImportError:
    import gdal

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

def un_zipfile(zip_file, out_dir):
    try:
        with zipfile.ZipFile(zip_file, 'r') as zip:
            for file in zip.filelist:
                if os.path.exists(os.path.join(out_dir, file.filename)):
                    continue
                else:
                    zip.extract(file, out_dir)
    except:
        print('Problem opening file %s !' % zip_file)
        return


def un_tar(tar_file, out_dir):
    try:
        with tarfile.open(tar_file) as tar:
            tar_files = tar.getnames()
            for itar_file in tar_files:
                if os.path.exists(os.path.join(out_dir, itar_file)):
                    continue
                tar.extract(itar_file, out_dir)
        os.remove(tar_file)
    except:
        print('Problem opening file %s !' % tar_file)
        return


def un_gz(gz_file, out_dir):

    try:

        with gzip.open(gz_file, 'rb') as gz:
            gz_data = gz.read()

    except:
        print('Problem opening file %s !' % gz_file)
        return

    """ungz gz file"""
    out_file = os.path.normpath(os.path.join(out_dir, gz_file[:-3]))

    if os.path.isfile(out_file):
        os.remove(out_file)

    with open(out_file, 'wb') as out:
        out.write(gz_data)

    return out_file

def run_un_zip(in_file, out_dir):

    extension = os.path.splitext(os.path.basename(in_file))[1]


    if extension == '.gz':

        file_name = os.path.splitext(os.path.splitext(os.path.basename(in_file))[0])[0]

        out_gz_dir = os.path.normpath(os.path.join(out_dir, file_name))
        if not os.path.isdir(out_gz_dir):
            os.mkdir(out_gz_dir)

        tar_file = un_gz(in_file, out_gz_dir)

        un_tar(tar_file, out_gz_dir)
    else:

        out_zip_dir = os.path.join(out_dir, os.path.splitext(os.path.basename(in_file))[0])
        if not os.path.isdir(out_zip_dir):
            os.mkdir(out_zip_dir)
        un_zipfile(in_file, out_zip_dir)


def main(in_dir, out_dir):

    if not os.path.isdir(out_dir):
        os.mkdir(out_dir)

    # 查询后缀为.zip和.gz的压缩包
    zip_list = search_file(in_dir, '.zip')
    gz_list = search_file(in_dir, '.gz')

    zip_files = zip_list + gz_list

    run_un_zip(gz_list[0], out_dir)

    if zip_files == []:
        sys.exit('no zip file')


    num_thread = int(multiprocessing.cpu_count()) - 1

    for zip in range(0, len(zip_files), num_thread):

        sub_zip_list = zip_files[zip: num_thread+zip]

        thread_list = []
        for izip in sub_zip_list:
            thread = Thread(target=run_un_zip, args=(izip, out_dir,))
            thread.start()
            thread_list.append(thread)

        for it in thread_list:
            it.join()

        progress(zip / len(zip_files))

    progress(1)


if __name__ == '__main__':

    start_time = time.time()

    if len(sys.argv[1:]) < 2:
        sys.exit('Problem reading input')
    # in_dir = r"D:\Data\Test_data\un_zip\in_dir"
    # out_dir = r"D:\Data\Test_data\un_zip\out_dir"

    in_dir = sys.argv[1]
    out_dir = sys.argv[2]
    main(in_dir, out_dir)

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))