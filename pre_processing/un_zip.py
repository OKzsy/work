#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/7/3 10:18

Description:
    对后缀为.gz和.zip的压缩文件包进行解压处理

Parameters
   in_file:压缩包文件路径
   out_dir:解压输出文件夹路径

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

        # out_zip_dir = os.path.join(out_dir, os.path.splitext(os.path.basename(in_file))[0])
        # if not os.path.isdir(out_zip_dir):
        #     os.mkdir(out_zip_dir)
        un_zipfile(in_file, out_dir)


def main(in_file, out_dir):

    if not os.path.isdir(out_dir):
        os.mkdir(out_dir)

    run_un_zip(in_file, out_dir)



if __name__ == '__main__':

    start_time = time.time()

    # if len(sys.argv[1:]) < 2:
    #     sys.exit('Problem reading input')
    in_file = r"F:\变化监测\工作.tar.gz"
    out_dir = r"F:\变化监测\L1C_T49SGU_A016374_20180811T030542"

    # in_file = sys.argv[1]
    # out_dir = sys.argv[2]
    main(in_file, out_dir)

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))