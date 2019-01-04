#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/7/5 14:29

Description:
    

Parameters
    

"""

import os
import sys
import time

from ftplib import FTP, error_perm

import numpy as np
import numexpr as ne
import pandas as pd

try:
    from osgeo import gdal
except ImportError:
    import gdal

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def walk_dir(f, ftp_dir, out_dir):

    try:
        f.cwd(ftp_dir)
    except error_perm:
        return  # ignore non-directores and ones we cannot enter
    # print (f.pwd())
    out_dir = os.path.join(out_dir, os.path.basename(ftp_dir))
    if not os.path.isdir(out_dir):
        os.mkdir(out_dir)

    names = f.nlst()
    for name in names:
        in_file = ftp_dir + '/' + name
        out_file = os.path.normpath(os.path.join(out_dir, name))
        try:
            with open(out_file, 'wb') as download_file:
                f.retrbinary('RETR ' + in_file, download_file.write)
        except:
            walk_dir(f, in_file, out_dir)

    # f.cwd(original_dir)

def main(ip, port, usr, password, out_dir):

    #
    # ip = '117.159.19.212'
    # port = 2121
    # usr = 'bob'
    # password = '12345'
    # 连接服务器 服务器编码位utf8
    ftp = FTP()

    try:
        ftp.connect(ip, port)
    except error_perm:
        sys.exit('%s ip or %d port error' % (ip, port))

    try:
        ftp.login(usr, password)
    except error_perm:
        ftp.quit()
        sys.exit('usr name or password error')


    # out_dir = r'D:\Data\Test_data\un_zip\out_dir\test_ftp'
    #
    # ip = '117.159.19.212'
    # port = 2121
    # usr = 'bob'
    # password = '12345'
    #
    # # 连接服务器 服务器编码位gbk
    # ftp = FTP()
    # ftp.connect(ip, port)
    # ftp.login(usr, password)
    ftp.encoding = 'utf-8'

    walk_dir(ftp, ftp.pwd(), out_dir)
    ftp.quit()




if __name__ == '__main__':
    start_time = time.time()

    if len(sys.argv[1:]) < 5:
        sys.exit('Problem reading input')

    main(sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5])

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))