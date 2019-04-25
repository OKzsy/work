#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/6/9 18:10

Description:


Parameters


"""
import os
import time
import csv
import sys
import tempfile
import subprocess
import shutil
import numpy as np
import multiprocessing as mp

def search_file(folder_path, file_extension):
    search_files = []
    for dirpath, dirnames, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(file_extension):
                search_files.append(os.path.normpath(os.path.join(dirpath, file)))
    return search_files


def run_6s(in_list):





    txt_list = in_list[:-3]
    temp_dir = in_list[-3]
    number = in_list[-2]
    out_dir = in_list[-1]


    for itxt in txt_list:
        ifile_name = '_'.join(os.path.splitext(os.path.basename(itxt))[0].split('_')[:-1])

        out_csvfile = os.path.join(out_dir, '%s_out.csv' % ifile_name)

        # 打开文本
        with open(itxt) as in_txt:
            in_data = in_txt.readlines()

        out_csv = open(out_csvfile, "w", newline='')

        scv_writer = csv.writer(out_csv)

        for i in range(number):

            iapparent_ref = '%.5f\n' % ((i + 1.0) / -number)
            i6s_in_data = in_data
            i6s_in_data[-1] = iapparent_ref

            i6s_in_file = os.path.join(temp_dir, '%s_in_%s.txt' % (ifile_name, (iapparent_ref[1:-1])))
            i6s_out_file = os.path.join(temp_dir, '%s_out_%s.txt' % (ifile_name, (iapparent_ref[1:-1])))

            with open(i6s_in_file, 'w') as i6s_in_txt:
                i6s_in_txt.writelines(i6s_in_data)

            # call 6s
            in_cmd = '"%s" < "%s" > "%s"' % ('sixsV1.1', i6s_in_file, i6s_out_file)
            subprocess.call(in_cmd, shell=True)
            # time.sleep(2)

            with open(i6s_out_file) as i6s_out_txt:
                i6s_out_data = i6s_out_txt.readlines()

            irad_value = float(i6s_out_data[196][47:-2])
            i6s_coefficients = i6s_out_data[200][47:-2].split(' ')
            while '' in i6s_coefficients:
                i6s_coefficients.remove('')
            i6s_coefficients = np.array(i6s_coefficients).astype(np.float)

            ixa = i6s_coefficients[0]
            ixb = i6s_coefficients[1]
            ixc = i6s_coefficients[2]

            iacr = (ixa * (irad_value) - ixb) / (1.0 + ixc * (ixa * (irad_value) - ixb))


            iout_data = [(i + 1.0) / number, irad_value, iacr]

            scv_writer.writerow(iout_data)

            print((i + 1.0) / number, irad_value, iacr)

            iout_data = None

        out_csv.close()
        scv_writer = None
        out_csv = None
def csv_merge(in_dir, out_csv):

    csv_files = search_file(in_dir, '.csv')
    bolck_names = ['gray', 'black', 'white']
    band_names = ['blue', 'green', 'red', 'nir', 'pan']

    bolck_names = ['red', 'black', 'gray']
    band_names = ['b1', 'b2', 'b3', 'b4', 'b5', 'b6', 'b7', 'b8', 'b9',
                  'b10', 'b11', 'b12', 'b13', 'b14', 'b15', 'b16', 'b17',
                  'b18', 'b19', 'b20', 'b21', 'b22', 'b23', 'b24', 'b25',
                  'b26', 'b27', 'b28', 'b29', 'b30', 'b31', 'b32']

    csv_file_sort = []
    all_csv_data = []

    for iblock in bolck_names:
        for iband in band_names:

            for icsv in csv_files:
                icsv_filename = os.path.splitext(os.path.basename(icsv))[0]
                if (iblock in icsv_filename) and (iband in icsv_filename):
                    csv_file_sort.append(icsv)
                    with open(icsv, 'r', newline='') as icsv_read:
                        icsv_data = icsv_read.read()
                        all_csv_data.append(icsv_data)
    out_data = all_csv_data[0].split('\r\n')

    for iall_csv_data in all_csv_data[1:]:
        iall_csv_data_list = iall_csv_data.split('\r\n')

        for i in range(len(out_data)):
            out_data[i] = out_data[i] + ',' + iall_csv_data_list[i]


    with open(out_csv, 'w', newline='') as out_csv:
        out_csv_writer = csv.writer(out_csv, dialect=("excel"))

        for iout_data in out_data:

            out_csv_writer.writerow(iout_data.split(','))

def main(in_dir, out_dir):

    sensor_id = os.path.basename(in_dir)

    # 建立缓存文件夹
    temp_dir = os.path.join(tempfile.gettempdir(), 'temp_6s_%s' % (sensor_id))
    if not os.path.isdir(temp_dir):
        os.mkdir(temp_dir)

    if not os.path.isdir(out_dir):
        os.mkdir(out_dir)


    number = 10000

    txt_list = search_file(in_dir, '.txt')
    #
    num_proc = int(mp.cpu_count() * 1 / 2)

    num_proc = int(mp.cpu_count())
    pool = mp.Pool(processes=num_proc)

    block_num_file = int(len(txt_list) / num_proc)

    for iproc in range(num_proc):

        if iproc == (num_proc - 1):
            sub_in_files = txt_list[(iproc * block_num_file):]
        else:
            sub_in_files = txt_list[(iproc * block_num_file): (iproc * block_num_file) + block_num_file]

        in_list = sub_in_files + [temp_dir, number, out_dir]

        pool.apply_async(run_6s, args=(in_list,))

        # progress(iproc / num_proc)
    pool.close()
    pool.join()

    shutil.rmtree(temp_dir)
    print('lookup table done')


if __name__ == '__main__':
    start_time = time.time()

    if len(sys.argv[1:]) < 2:
        sys.exit('Problem reading input')

    in_dir = sys.argv[1]
    out_dir = sys.argv[2]


    # in_dir = r'D:\Data\Test_data\dingbiao\6s_in\Skysat8'
    # sixsv_path = r"D:\Document\RS_process\6S\compile_package\6SV-1.1\sixsV1.1"
    # out_dir = r'D:\Data\Test_data\dingbiao\6s_out\skysat8'
    #
    # in_dir = r'D:\Data\Test_data\oubite_20180807\6s_in'
    # out_dir = r'D:\Data\Test_data\oubite_20180807\6s_out'

    main(in_dir, out_dir)

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))