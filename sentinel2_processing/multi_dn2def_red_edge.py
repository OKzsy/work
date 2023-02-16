#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/10/5 15:07
# @Author  : zhaoss
# @FileName: multi_dn2def_red_edge.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters
band_list = [2, 3, 4, 5, 6, 7, 8a, 8]

"""

import os
import time
import sys
import shutil
import zipfile
import glob
import gc
import subprocess
import tempfile
import fnmatch
import random,string
import numpy as np
import xml.etree.ElementTree as ET
import multiprocessing.dummy as mp

from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def un_zip(zip_file, out_dir):
    try:
        zip = zipfile.ZipFile(zip_file, 'r')
        for name in zip.namelist():
            if os.path.exists(os.path.join(out_dir, name)):
                continue
            else:
                zip.extract(name, out_dir)
        zip.close()
    except Exception as e:
        print(e)
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
    jp2_20_list = ['B02_20', 'B03_20', 'B04_20', 'B05_20', 'B06_20',
                   'B07_20', 'B8A_20', 'B11_20', 'SCL_20m', 'CLDPRB_20m']

    out_list = []

    for band_pos in jp2_20_list:
        for jp2_file in in_list:
            band_name = os.path.splitext(os.path.basename(jp2_file))[0]

            if band_pos in band_name:
                out_list.append(jp2_file)

    return out_list


def searchfiles(dirpath, partfileinfo='*', recursive=False):
    """列出符合条件的文件（包含路径），默认不进行递归查询，当recursive为True时同时查询子文件夹"""
    # 定义结果输出列表
    filelist = []
    # 列出根目录下包含文件夹在内的所有文件目录
    pathlist = glob.glob(os.path.join(os.path.sep, dirpath, "*"))
    # 逐文件进行判断
    for mpath in pathlist:
        if os.path.isdir(mpath):
            # 默认不判断子文件夹
            if recursive:
                filelist += searchfiles(mpath, partfileinfo, recursive)
        elif fnmatch.fnmatch(os.path.basename(mpath), partfileinfo):
            filelist.append(mpath)
        # 如果mpath为子文件夹，则进行递归调用，判断子文件夹下的文件

    return filelist


def corner_to_geo(sample, line, dataset):
    """
    :param sample: 列号
    :param line:   行号
    :param dataset: 所在影像的数据集
    :return: 指定行列号的经纬度
    """
    # 计算指定行,列号的地理坐标
    Geo_t = dataset.GetGeoTransform()
    # 计算地理坐标
    geoX = Geo_t[0] + sample * Geo_t[1]
    geoY = Geo_t[3] + line * Geo_t[5]
    return geoX, geoY


def reproject_dataset(src_ds):
    """
    :param src_ds: 待重采样影像的数据集
    :return: 调用ReprojectImage对影像进行重采样,重采样后影像的分辨率为原始影像分辨率,
    投影信息为WGS84。
    """
    # 定义目标投影
    oSRS = osr.SpatialReference()
    oSRS.SetWellKnownGeogCS("WGS84")
    # 获取原始投影
    src_prj = src_ds.GetProjection()
    oSRC = osr.SpatialReference()
    oSRC.ImportFromWkt(src_prj)
    # 测试投影转换
    oSRC.SetTOWGS84(0, 0, 0)
    tx = osr.CoordinateTransformation(oSRC, oSRS)

    # 获取原始影像的放射变换参数
    geo_t = src_ds.GetGeoTransform()
    x_size = src_ds.RasterXSize
    y_size = src_ds.RasterYSize
    bandCount = src_ds.RasterCount
    dataType = src_ds.GetRasterBand(1).DataType
    if oSRC.GetAttrValue("UNIT") == "metre":
        new_x_size = geo_t[1] * 10 ** (-5)
        new_y_size = geo_t[5] * 10 ** (-5)
    else:
        new_x_size = geo_t[1]
        new_y_size = geo_t[5]
    # 获取影像的四个角点地理坐标
    # 左上
    old_ulx, old_uly = corner_to_geo(0, 0, src_ds)
    # 右上
    old_urx, old_ury = corner_to_geo(x_size, 0, src_ds)
    # 左下
    old_dlx, old_dly = corner_to_geo(0, y_size, src_ds)
    # 右下
    old_drx, old_dry = corner_to_geo(x_size, y_size, src_ds)

    # 计算出新影像的边界
    # 左上
    (new_ulx, new_uly, new_ulz) = tx.TransformPoint(old_ulx, old_uly, 0)
    # 右上
    (new_urx, new_ury, new_urz) = tx.TransformPoint(old_urx, old_ury, 0)
    # 左下
    (new_dlx, new_dly, new_dlz) = tx.TransformPoint(old_dlx, old_dly, 0)
    # 右下
    (new_drx, new_dry, new_drz) = tx.TransformPoint(old_drx, old_dry, 0)
    # 统计出新影像的范围
    # 左上经度
    ulx = min(new_ulx, new_dlx)
    # 左上纬度
    uly = max(new_uly, new_ury)
    # 右下经度
    lrx = max(new_urx, new_drx)
    # 右下纬度
    lry = min(new_dly, new_dry)
    # 创建重投影后新影像的存储位置
    mem_drv = gdal.GetDriverByName('MEM')
    # 根据计算的参数创建存储空间
    dest = mem_drv.Create('', int((lrx - ulx) / new_x_size),
                          int((uly - lry) / -new_y_size), bandCount, dataType)
    # 计算新的放射变换参数
    new_geo = (ulx, new_x_size, geo_t[2], uly, geo_t[4], new_y_size)
    # 为重投影结果设置空间参考
    dest.SetGeoTransform(new_geo)
    dest.SetProjection(oSRS.ExportToWkt())
    # 执行重投影和重采样
    res = gdal.ReprojectImage(src_ds, dest,
                              src_prj, oSRS.ExportToWkt(),
                              gdal.GRA_NearestNeighbour, callback=progress)
    return dest


def update_vrt(vrt_file, flag_list):
    # 解析vrt文件
    fj = open(vrt_file, 'r')
    vrt_str = fj.read()
    root = ET.fromstring(vrt_str)
    for flag in flag_list:
        # 获取波段
        tmp_flag = flag.split('_')[-1]
        band_id = tmp_flag.split('.')[0]
        # 匹配节点
        for node in root.findall('VRTRasterBand'):
            if node.attrib['band'] == band_id:
                node.find('SimpleSource').find('SourceFilename').text = flag
                break
    # 转为新的字符串
    new_vrt_str = ET.tostring(root, encoding='unicode')
    fj.close()
    return new_vrt_str


def genRandomfile(dir='', prefix='', suffix='', slen=10):
    rand_str = ''.join(random.sample(string.ascii_letters + string.digits, slen))
    tempfile_name = prefix + rand_str + suffix
    if dir:
        temp_file = os.path.join(dir, tempfile_name)
    else:
        temp_file = tempfile_name
    if not os.path.exists(temp_file):     
        return temp_file
    else:
        return genRandomfile(dir, prefix, suffix, slen=10)


def cld_mask(src_dst):
    uncld_files_path = []
    bandcount = src_dst.RasterCount
    xsize = src_dst.RasterXSize
    ysize = src_dst.RasterYSize
    # 获取云掩膜波段
    cld_data = src_dst.GetRasterBand(bandcount).ReadAsArray()
    # 根据阈值生成云掩膜
    cld_mask = cld_data <= 50
    # 去除RGB波段的云
    tif_drv = gdal.GetDriverByName('GTiff')
    for iband in range(1, 10):
        tmp_band = src_dst.GetRasterBand(iband)
        dtype = tmp_band.DataType
        tmp_data = tmp_band.ReadAsArray()
        # 创建内存文件
        mem_file = genRandomfile(prefix='/vsimem/',suffix='_{}.tif'.format(str(iband)))
        tmp_ds = tif_drv.Create(mem_file, xsize, ysize, 1, dtype)
        tmp_data_uncld = tmp_data * cld_mask
        tmp_ds.GetRasterBand(1).WriteArray(tmp_data_uncld)
        tmp_ds = tmp_data_uncld = tmp_data = None
        uncld_files_path.append(mem_file)
    src_dst = cld_data = cld_mask = None
    return uncld_files_path


def dn2ref(out_dir, zip_file):
    # zip所在父目录
    zip_dir = os.path.dirname(zip_file)
    zip_name = os.path.splitext(os.path.basename(zip_file))[0]
    zip_file_name = zip_name
    temp_dir = tempfile.mkdtemp(dir=out_dir, suffix='_un_zip')
    if not os.path.isdir(temp_dir):
        os.mkdir(temp_dir)
    zip_value = un_zip(zip_file, temp_dir)
    if zip_value == 0:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return
    # 增加用于兼容不同网站下载的Sen2数据
    tag = zip_name[0:3]
    if tag == 'L1C':
        zip_name = list(os.walk(temp_dir))[0][1][0][0:-5]
    # 使用Sen2Cor计算地表反射率
    safe_dir = os.path.join(temp_dir, '%s.SAFE' % zip_name)
    if not os.path.isdir(safe_dir):
        sys.exit('No %s.SAFE dir' % zip_name)
    subprocess.call('L2A_Process.bat %s' % safe_dir)
    # subprocess.call('D:\Sen2Cor-02.09.00-win64\L2A_Process.bat %s' % safe_dir)
    # os.system('L2A_Process %s' % safe_dir)

    L2_dir_list = list(zip_name.split('_'))
    L2_dir_list[1] = 'MSIL2A'
    L2_dir_list[3] = '*'
    L2_dir_list[6] = '*'
    L2_dir_name_regex = os.path.join(temp_dir, '_'.join(L2_dir_list))
    L2_dir = glob.glob(L2_dir_name_regex)[0]

    L2_data_dir = os.path.join(L2_dir, 'GRANULE')

    xml_file = searchfiles(L2_data_dir, '*.xml', recursive=True)[0]

    xml_dir = os.path.dirname(xml_file)
    jp2_files = searchfiles(xml_dir, '*.jp2', recursive=True)

    if jp2_files == []:
        sys.exit()
    xml_name = os.path.basename(xml_dir)

    jp2_10_files = get_10_jp2(jp2_files)
    if jp2_10_files == []:
        sys.exit()

    jp2_20_files = get_20_jp2(jp2_files)
    if jp2_20_files == []:
        sys.exit()
    # 增加红边波段
    jp2_10_files[4:4] = jp2_20_files[3:8]
    # 增加云掩膜波段
    jp2_10_files.append(jp2_20_files[9])
    vrt_10_file = os.path.join(safe_dir, '%s_10m.vrt' % xml_name)
    vrt_options = gdal.BuildVRTOptions(resolution='user', xRes=10, yRes=10, separate=True,
                                       resampleAlg='bilinear')
    vrt_10_dataset = gdal.BuildVRT(vrt_10_file, jp2_10_files, options=vrt_options)
    # # 依据云掩膜去除数据中的云,只去除RGB波段
    jp2_10_uncld_files = cld_mask(vrt_10_dataset)
    # 修改vrt_10_file文件
    tempvrtfile = genRandomfile(dir=safe_dir, prefix="uncloud_", suffix=".vrt")
    vrt_10_dataset.GetDriver().CreateCopy(tempvrtfile, vrt_10_dataset)
    jp2_10_uncld_vrt = update_vrt(tempvrtfile, jp2_10_uncld_files)
    vrt_uncld_ds = gdal.Open(jp2_10_uncld_vrt)
    # 重投影
    dst = reproject_dataset(vrt_uncld_ds) 
    # 释放内存文件
    for mem_file in jp2_10_uncld_files:
        gdal.Unlink(mem_file)
    gc.collect()
    # 存储文件
    isub_ref_dir = os.path.join(out_dir, zip_file_name)
    if not os.path.isdir(isub_ref_dir):
        os.mkdir(isub_ref_dir)

    out_driver = gdal.GetDriverByName('GTiff')
    out_10_file = os.path.join(isub_ref_dir, '%s_ref_10m.tif' % xml_name)
    print("Start exporting images at 10 meters resolution", flush=True)
    out_10_ds = out_driver.CreateCopy(out_10_file, dst, callback=progress)

    vrt_10_dataset = vrt_uncld_ds = dst = out_10_ds = None
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    


def main(in_dir, out_dir):
    if not os.path.isdir(out_dir):
        os.mkdir(out_dir)

    # 搜索输入路径下所有zip文件
    zip_files = searchfiles(in_dir, '*.zip', recursive=True)

    if zip_files == []:
        sys.exit('no zip file')
    # 建立多个进程
    # jobs = os.cpu_count() if os.cpu_count() < len(zip_files) else len(zip_files)
    jobs = 4
    pool = mp.Pool(processes=jobs)
    for izip in zip_files:
        # dn2ref(out_dir, izip)
        pool.apply_async(dn2ref, args=(out_dir, izip,))
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
    in_dir = r"F:\test\S2\data"
    out_dir = r"F:\test\data_out\new"
    main(in_dir, out_dir)

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))
