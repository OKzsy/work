#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/6/7 17:47

Description:
    根据光谱响应函数积分光谱，并对光谱和光谱响应函数进行2.5nm间隔的光谱重采样,作为6S的输入参数，输出定标参量
    注意：代码种光谱范围和6s可执行文件（6s默认实在环境变量种）需要根据需要配置

Parameters
    参数1：光谱文件路径
    参数2：定标卫星的光谱响应函数文件路径
    参数3：6s输入参数实例文件路径
    参数4：输出文件夹（输出包括6s输出文件，以及最终模拟辐亮度文件）

"""

import os
import sys
import time
import csv
import platform
import subprocess
import operator
import multiprocessing as mp
import numpy as np
from scipy import interpolate

try:
    from osgeo import gdal
except ImportError:
    import gdal

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def sort_6s_txt(in_list):
    out_txt_dict = {}
    # 排序txt
    for iout_txt in in_list:
        file_id = os.path.splitext(os.path.basename(iout_txt))[0].split('_')[0]
        out_txt_dict[int(file_id)] = iout_txt
    # 按照序号排序
    out_txt_list = sorted(out_txt_dict.items(), key=operator.itemgetter(0), reverse=False)

    return out_txt_list
def search_file(folder_path, file_extension):
    search_files = []
    for dirpath, dirnames, files in os.walk(folder_path):
        for file in files:
            if (file.lower().endswith(file_extension)):
                search_files.append(os.path.normpath(os.path.join(dirpath, file)))
    return search_files

def get_all_point_spec(spec_file):
    # 读取实测光谱数据
    with open(spec_file, 'r') as spec:
        spec_str = spec.readlines()

    point_id = [str(i).replace(' ', '').replace('\n', '') for i in spec_str[0].split(',')]
    spec_list = []
    for ispec_str in spec_str[1:]:
        ispec_data = ispec_str.replace('\n', '').split(',')

        while '' in ispec_data:
            ispec_data.remove('')

        spec_list.append([np.float(i) for i in ispec_data])

    spec_array = np.array(spec_list)

    return spec_array, point_id

def interp_band_range(band_range):
    band_interp = np.arange(band_range[0], band_range[1], 2.5)
    if band_interp[-1] == band_range[1]:
        return band_interp
    else:
        return np.append(band_interp, band_range[1])
def set_6s_in_txt(sample_6s_txt, spec_array, point_name, spec_func_array, band_name, out_6s_dir):

    spec_band_range = spec_array[:, 0].astype(np.int)
    spec_func_band_range = spec_func_array[:, 0].astype(np.int)

    # 查询波段相交区域
    func_ind = []
    spectra_ind = []
    for ifunc_band in range(len(spec_func_band_range)):
        for ispec_band in range(len(spec_band_range)):
            if spec_band_range[ispec_band] == spec_func_band_range[ifunc_band]:
                func_ind.append(ifunc_band)
                spectra_ind.append(ispec_band)
    spec_func_sub_list = []
    spec_sub_list = []
    spec_func_band_sub_list = []
    spec_band_sub_list = []
    for ind in range(len(func_ind)):
        spec_func_sub_list.append(spec_func_array[func_ind[ind], 1:])
        spec_sub_list.append(spec_array[spectra_ind[ind], 1:])
        spec_func_band_sub_list.append(spec_func_band_range[func_ind[ind]])
        spec_band_sub_list.append(spec_band_range[spectra_ind[ind]])

    spec_func_sub_array = np.array(spec_func_sub_list)
    spec_sub_array = np.array(spec_sub_list)
    spec_func_band_sub_range = np.array(spec_func_band_sub_list)
    spec_band_sub_range = np.array(spec_band_sub_list)

    sixs_in_list = []

    for ipoint in range(len(point_name[1:])):
        ipoint_name = point_name[1:][ipoint].replace(' ', '').replace('\n', '')
        ipoint_spec_data = spec_sub_array[:, ipoint]


        # planet光谱范围:
        # spec_range = [(455, 515), (500,590), (590,670), (780,860)]
        # 根据需要进行配置
        # spec_range = [(450, 515), (515, 595), (605, 695), (740, 900), (450, 900)]
        for iband in range(len(band_name[1:])):
            iband_name = band_name[1:][iband].replace(' ', '').replace('\n', '')
            iband_sepc_func_data = spec_func_sub_array[:, iband]
            iband_func_range_ind = np.where(iband_sepc_func_data >= 0.4)
            iband_func_range_min = np.min(spec_func_band_sub_range[iband_func_range_ind])
            iband_func_range_max = np.max(spec_func_band_sub_range[iband_func_range_ind])

            # iband_func_range_min = spec_range[iband][0]
            # iband_func_range_max = spec_range[iband][1]
            print('%s (%d, %d)' % (iband_name, iband_func_range_min, iband_func_range_max))

            iband_interp_func_data = interp_band_range([iband_func_range_min, iband_func_range_max])
            # 插值光谱响应函数
            iband_interp_func = interpolate.interp1d(spec_func_band_sub_range.astype(np.float), iband_sepc_func_data,
                                                     kind="cubic")

            iband_interp_sepc = interpolate.interp1d(spec_band_sub_range.astype(np.float), ipoint_spec_data,
                                                     kind="cubic")
            iband_25nm_func = iband_interp_func(np.array(iband_interp_func_data))
            iband_25nm_func[iband_25nm_func > 1] = 1
            iband_25nm_spec = iband_interp_sepc(np.array(iband_interp_func_data))

            # 卷积光谱
            real_sepc_data = np.dot(iband_25nm_spec, iband_25nm_func) / np.sum(iband_25nm_func)

            with open(sample_6s_txt) as in_txt:
                in_data = in_txt.readlines()

            iout_data = in_data
            iout_data[43] = '%.4f %.4f\n' % (iband_func_range_min / 1000.0, iband_func_range_max / 1000.0)

            iout_data[44] = ' '.join(['%.4f' % i for i in iband_25nm_func]) + '\n'

            iout_data[48] = '%.4f' % float(real_sepc_data) + '\n'


            iout_txt = os.path.join(out_6s_dir, '%d_%s_%s_in.txt' % (ipoint*len(band_name[1:])+iband+1, ipoint_name, iband_name))

            with open(iout_txt, 'w') as i6s_in_txt:
                i6s_in_txt.writelines(iout_data)

            iout_data = None
            in_data = None
            sixs_in_list.append(iout_txt)
    return sixs_in_list


def run_6s(in_list):

    txt_list = in_list[0]
    out_6s_dir = in_list[1]

    for itxt in txt_list:

        ifile_name = '_'.join(os.path.splitext(os.path.basename(itxt))[0].split('_')[:-1])

        iout_file = os.path.join(out_6s_dir, '%s_out.txt' % (ifile_name))

        # call 6s 需要加入到环境变量, 6s可执行性文件, 命名可能不一致
        in_cmd = '"%s" < "%s" > "%s"' % ("sixsV1.1", itxt, iout_file)
        subprocess.call(in_cmd, shell=True)
        # time.sleep(1)

def get_rad(in_dir, out_dir, band_name, out_file):

    # set output csv file
    out_csv = open(out_file, 'w', newline='')
    out_csv_writer = csv.writer(out_csv)
    out_csv_writer.writerow([r'id\band'] + band_name[1:] + band_name[1:] + band_name[1:])

    in_6s_txt_list = sort_6s_txt(search_file(in_dir, '.txt'))
    out_6s_txt_list = sort_6s_txt(search_file(out_dir, '.txt'))

    for itxt in range(0, len(in_6s_txt_list), len(band_name[1:])):
        ipoint_out_txt_list = out_6s_txt_list[itxt: itxt + len(band_name[1:])]
        ipoint_in_txt_list = in_6s_txt_list[itxt: itxt + len(band_name[1:])]

        ipoint_name = str(os.path.splitext(os.path.basename(list((ipoint_out_txt_list)[0])[1]))).split('_')[1]

        ipoint_rad_list = []
        ipoint_coef_list = []
        ipoint_ref_list = []

        for iband in range(len(ipoint_in_txt_list)):
            # 打开文本
            with open(list(ipoint_in_txt_list[iband])[1]) as i6s_in_txt:
                i6s_in_data = i6s_in_txt.readlines()

            iref_ref = float(i6s_in_data[48].replace('\n', ''))

            with open(list(ipoint_out_txt_list[iband])[1]) as i6s_out_txt:
                i6s_out_data = i6s_out_txt.readlines()

            i6s_data = i6s_out_data[99].replace('\n', '').split(' ')
            while '' in i6s_data:
                i6s_data.remove('')
            i6s_coefficients = float(i6s_data[3])
            irad_value = float(i6s_data[6])

            ipoint_rad_list.append(irad_value)
            ipoint_coef_list.append(i6s_coefficients)
            ipoint_ref_list.append(iref_ref)

        out_csv_writer.writerow([ipoint_name] + ipoint_rad_list + ipoint_coef_list + ipoint_ref_list)
        print([ipoint_name] + ipoint_rad_list + ipoint_coef_list + ipoint_ref_list)

    out_csv.close()
    out_csv_writer = None
    out_csv = None


def main(spec_file, spec_func_file, sample_6s_txt, out_dir):

    spec_array, point_name = get_all_point_spec(spec_file)
    spec_func_array, band_name = get_all_point_spec(spec_func_file)
    in_6s_dir = os.path.join(out_dir, '6s_in_txt')

    if not os.path.exists(in_6s_dir):
        os.mkdir(in_6s_dir)
    sixs_in_list = set_6s_in_txt(sample_6s_txt, spec_array, point_name, spec_func_array, band_name, in_6s_dir)
    out_rad_ref = os.path.join(out_dir, 'all_rad_ref.csv')

    # 建立进程池
    out_6s_dir = os.path.join(out_dir, '6s_out_txt')
    if not os.path.exists(out_6s_dir):
        os.mkdir(out_6s_dir)
    num_proc = int(mp.cpu_count() - 1)

    if len(sixs_in_list) < num_proc:
        num_proc = len(sixs_in_list)
        block_num_file = 1
    else:
        block_num_file = int(len(sixs_in_list) / num_proc)

    result_list = []

    pool = mp.Pool(processes=num_proc)

    for iproc in range(num_proc):

        if iproc == (num_proc - 1):
            sub_in_files = sixs_in_list[(iproc * block_num_file):]
        else:
            sub_in_files = sixs_in_list[(iproc * block_num_file): (iproc * block_num_file) + block_num_file]

        in_list = [sub_in_files, out_6s_dir]

        result = pool.apply_async(run_6s, args=(in_list,))
        result_list.append(result)

    for r in result_list:
        print(r.get())

    pool.close()
    pool.join()
    # 获取辐亮度、表观反射率、地表反射率
    get_rad(in_6s_dir, out_6s_dir, band_name, out_rad_ref)

if __name__ == '__main__':
    start_time = time.time()

    if len(sys.argv[1:]) < 4:
        sys.exit('Problem reading input')
    # spec_file = r"D:\Data\Test_data\radiation_calobration\planet_2018080711\2018080711_HH2.csv"
    # func_file = r"D:\Data\Test_data\radiation_calobration\planet_2018080811\planet_func.csv"
    # sample_6s_txt = r"D:\Data\Test_data\radiation_calobration\planet_2018080711\6s_sample_0807.txt"
    # out_dir = r'D:\Data\Test_data\radiation_calobration\planet_2018080711'

    # spec_file = r"D:\Data\Test_data\radiation_calobration\planet_2018080811\2018080811_FS4.csv"
    # func_file = r"D:\Data\Test_data\radiation_calobration\planet_2018080811\planet_func.csv"
    # sample_6s_txt = r"D:\Data\Test_data\radiation_calobration\planet_2018080811\6s_sample.txt"
    # out_dir = r'D:\Data\Test_data\radiation_calobration\planet_2018080811'

    # spec_file = r"D:\Data\Test_data\radiation_calobration\planet_2018060513\201806051330_FS4_txt.csv"
    # func_file = r"D:\Data\Test_data\radiation_calobration\planet_2018060513\rsr_u9_norm_copy.csv"
    # sample_6s_txt = r"D:\Data\Test_data\radiation_calobration\planet_2018060513\6s_sample.txt"
    # out_dir = r'D:\Data\Test_data\radiation_calobration\planet_2018060513'
    spec_file = sys.argv[1]
    func_file = sys.argv[2]
    sample_6s_txt = sys.argv[3]
    out_dir = sys.argv[4]

    main(spec_file, func_file, sample_6s_txt, out_dir)

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))