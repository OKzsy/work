#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/12/18 10:21

Description:
    基于地理国情或者农经确权等复杂矢量，对影像进行掩膜处理。

Parameters
    参数1：输入待掩膜的影像
    参数2：输入地理国情或确权矢量
    参数3：设置输出影像的nodata值
    参数4：输出掩膜影像路径

"""

import os
import sys
import time
import random
import string
import tempfile
import shutil
import platform
import numpy as np

try:
    from osgeo import gdal, ogr
except ImportError:
    import gdal, ogr

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def main(in_file, shp_file, nodata, out_file):

    # 新建缓存文件夹
    sys_str = platform.system()
    if (sys_str == 'Windows'):
        temp_dir = os.path.join(tempfile.gettempdir(), 'gdal_mask2')
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.mkdir(temp_dir)
    else:
        rand_str = ''.join(random.sample(string.ascii_letters + string.digits, 4))
        temp_dir = os.path.join(r'/data6', 'gdal_%s' % rand_str)
        if not os.path.exists(temp_dir):
            os.mkdir(temp_dir)
    # 打开影像
    source_dataset = gdal.Open(in_file)
    if source_dataset is None:
        sys.exit('Problem opening file %s !' % in_file)

    # 获取数据基本信息
    xsize = source_dataset.RasterXSize
    ysize = source_dataset.RasterYSize
    num_band = source_dataset.RasterCount
    data_type = source_dataset.GetRasterBand(1).DataType
    in_geo = source_dataset.GetGeoTransform()
    source_proj = source_dataset.GetProjectionRef()

    mask_file = os.path.join(temp_dir, '%s_mask.tif' % (os.path.splitext(os.path.basename(shp_file))[0]))
    out_driver = gdal.GetDriverByName('GTiff')
    if os.path.exists(mask_file):
        out_driver.Delete(mask_file)

    print('shape to mask raster start...')
    gdal.Rasterize(mask_file, shp_file, burnValues = 1,
                   xRes = abs(in_geo[1] / 2), yRes=abs(in_geo[5] / 2) ,
                   outputType = data_type, callback = progress)
    # gdal.Rasterize(mask_file, shp_file, burnValues=1,
    #                xRes=abs(in_geo[1]), yRes=abs(in_geo[5]),
    #                outputType=data_type, callback=progress)
    print('shape to mask raster done.')

    print('mask raster start...')
    mask_sds = gdal.Open(mask_file)
    if mask_sds is None:
        sys.exit('Problem opening file %s !' % mask_file)

    separate_files = []
    for iband in range(num_band):
        single_file = os.path.join(temp_dir,
                                '%s_band%d.tif' % (os.path.splitext(os.path.basename(in_file))[0], iband+1))

        single_sds = out_driver.Create(single_file, xsize, ysize, 1, data_type)

        single_sds.GetRasterBand(1).WriteArray(source_dataset.GetRasterBand(1+iband).ReadAsArray(), 0, 0)

        single_sds.SetGeoTransform(in_geo)
        single_sds.SetProjection(source_proj)
        single_sds = None
        # gdal.Translate(single_file, in_file, bandList=[iband+1])
        separate_files.append(single_file)

        progress((1+iband) / num_band * 0.5)

    separate_files.append(mask_file)
    vrt_file = os.path.join(temp_dir,
                            '%s_vrt.vrt' % (os.path.splitext(os.path.basename(in_file))[0]))

    gdal.BuildVRT(vrt_file, separate_files,
                  resolution='user', xRes=abs(in_geo[1]), yRes=abs(in_geo[5]),
                  separate=True, options=['-r', 'near'])
    vrt_sds = gdal.Open(vrt_file)

    if vrt_sds is None:
        sys.exit('Problem opening file %s !' % vrt_file)

    out_geotransform = vrt_sds.GetGeoTransform()
    out_projection = vrt_sds.GetProjectionRef()
    out_xsize = vrt_sds.RasterXSize
    out_ysize = vrt_sds.RasterYSize

    out_sds = out_driver.Create(out_file, out_xsize, out_ysize, num_band, data_type)
    num_xblock = 10000

    for xoffset in range(0, out_xsize, num_xblock):
        if xoffset + num_xblock < out_xsize:
            num_xsize = num_xblock
        else:
            num_xsize = out_xsize - xoffset

        block_data = vrt_sds.ReadAsArray(xoffset, 0, num_xsize, ysize)

        ind = np.where(block_data[num_band, :, :] == 0)

        for iband in range(num_band):
            block_data[iband, :, :][ind] = nodata
            out_sds.GetRasterBand(iband + 1).WriteArray(block_data[iband, :, :], xoffset, 0)
        block_data = None
        ind = None

    # ind = np.where(out_sds.ReadAsArray()[num_band, :, :].reshape(out_ysize, out_xsize) == 0)
    #
    # for iband in range(num_band):
    #     band_data = out_sds.ReadAsArray()[iband, :, :].reshape(out_ysize, out_xsize)
    #     band_data[ind] = nodata
    #     out_sds.GetRasterBand(iband + 1).WriteArray(band_data, 0, 0)
    #     band_data = None
    #
        progress((xoffset + num_xsize + 1) / out_xsize + 0.5)
    #
    out_sds.SetGeoTransform(out_geotransform)
    out_sds.SetProjection(out_projection)
    data = None
    mask_data = None
    vrt_sds = None
    out_sds = None
    source_dataset = None
    mask_sds = None
    print('mask raster done {}.'.format(temp_dir))
    shutil.rmtree(temp_dir)
    print()
    print('all done')

if __name__ == '__main__':
    # 注册所有gdal的驱动
    gdal.AllRegister()
    gdal.SetConfigOption("gdal_FILENAME_IS_UTF8", "YES")

    start_time = time.time()

    # if len(sys.argv[1:]) < 4:
    #     sys.exit('Problem reading input')
    #
    # in_file = sys.argv[1]
    # shp_file = sys.argv[2]
    # nodata = float(sys.argv[3])
    # out_file = sys.argv[4]

    #
    # in_file = r"D:\Data\Test_data\clip_20181218\test2\GF2_20180327_sha_test.tif"
    # shp_file = r"D:\Data\Test_data\clip_20181218\test2\0120_test.shp"
    # out_file = r"D:\Data\Test_data\clip_20181218\test2\GF2_20180327_sha_test_mask2.tif"
    #
    in_file = r"F:\test_data\clipraster\SatImage.tif"
    shp_file = r"F:\test_data\clipraster\county.shp"
    out_file = r"F:\test_data\clipraster\out\country_jg.tif"
    nodata = 0
    main(in_file, shp_file, nodata, out_file)
    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))