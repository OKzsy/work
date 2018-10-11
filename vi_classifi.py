#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2017.7.3

dscription:
    Calculation NDVI from multispectral file

parameters:
    in_file: input multispectral file path
    out_file: output ndvi file path
    nir_pos,red_pos:pos of nir band and red band in  multispectral file(options).like(4,3)

"""
__author__ = "tianjg"

import os
import sys
import time

import numpy as np
from scipy import ndimage

try:
    from osgeo import gdal
except ImportError:
    import gdal


def Sieve_filter(in_file, out_file, size):
    source_dataset = gdal.Open(in_file)
    if source_dataset is None:
        sys.exit('Problem opening file %s!' % in_file)

    xsize = source_dataset.RasterXSize
    ysize = source_dataset.RasterYSize
    geotransform = source_dataset.GetGeoTransform()
    projection = source_dataset.GetProjectionRef()
    in_band = source_dataset.GetRasterBand(1)
    data1 = in_band.ReadAsArray(0, 0, xsize, ysize)
    # in_band.SetNoDataValue(-999)
    #    out_file=in_file[:-4]+'_sieve.tif'
    #    if  os.path.exists(out_file):
    #        os.remove(out_file)
    #
    out_driver = gdal.GetDriverByName('GTIFF')
    out_dataset = out_driver.Create(out_file, xsize, ysize, 1, gdal.GDT_Byte)
    out_band = out_dataset.GetRasterBand(1)
    result_sieve = gdal.SieveFilter(in_band, None, out_band, size, 8, callback=None)
    data = out_band.ReadAsArray(0, 0, xsize, ysize)
    #    if len(data[np.where(data==1)])<=2**10:
    #
    #        sys.exit('the number of water point too few, can not do Raster To Polygon')

    out_band.WriteArray(ndimage.binary_dilation(out_band.ReadAsArray(), iterations=1), 0, 0)
    out_band.SetNoDataValue(0)
    out_dataset.SetGeoTransform(geotransform)
    out_dataset.SetProjection(projection)

    out_band = None
    source_dataset = None
    out_dataset = None

    print('ok')


def main(in_file, out_file):
    source_dataset = gdal.Open(in_file)
    if source_dataset is None:
        sys.exit('Problem opening file %s !' % in_file)

    # 获取数据基本信息
    xsize = source_dataset.RasterXSize
    ysize = source_dataset.RasterYSize
    num_band = source_dataset.RasterCount
    geotransform = source_dataset.GetGeoTransform()
    projection = source_dataset.GetProjectionRef()
    data_type = source_dataset.GetRasterBand(1).DataType

    if num_band < 4:
        sys.exit('number of band is %d ! ' % num_band)

    driver = gdal.GetDriverByName('GTiff')

    if os.path.exists(out_file):
        driver.Delete(out_file)

    driver = gdal.GetDriverByName('GTiff')
    out_dataset = driver.Create(out_file, xsize, ysize, 1, gdal.GDT_Byte)
    out_band = out_dataset.GetRasterBand(1)

    out_data = np.zeros((ysize, xsize), dtype=np.uint8)

    blue_data = source_dataset.GetRasterBand(1).ReadAsArray(0, 0, xsize, ysize)
    green_data = source_dataset.GetRasterBand(2).ReadAsArray(0, 0, xsize, ysize)
    red_data = source_dataset.GetRasterBand(3).ReadAsArray(0, 0, xsize, ysize)
    nir_data = source_dataset.GetRasterBand(4).ReadAsArray(0, 0, xsize, ysize)

    # ndvi_den = (nir_data + red_data)
    #
    # ndvi_den[ndvi_den == 0] = -3000
    # (red_data < 870) & (nir_data > 3500)   (green_data >= 800) & (green_data <= 1300) & (blue_data < 2800) && (gndvi >= 5000) & (gndvi <= 5600)
    # ndvi = (nir_data - red_data)* 1.0 / ndvi_den
    # & (nir_data > 3000)
    gndvi = ((nir_data-green_data) * 1.0 / (green_data + nir_data + 0.0000001)) * 10000

    ind = np.where(
        (green_data >= 1150) & (green_data <= 1500) & (nir_data > 3300) & (nir_data < 4300) & (red_data < 1900) &
        (red_data > 1000) & (gndvi < 4900))
    # ss = len(out_data[ind])

    out_data[ind] = 1
    # out_band.WriteArray(ndimage.binary_dilation(out_data, iterations = 1), 0, 0)
    out_band.WriteArray(out_data, 0, 0)

    out_band.SetNoDataValue(0)
    out_data = None
    green_data = None
    ndvi = None
    red_data = None
    nir_data = None

    out_dataset.SetGeoTransform(geotransform)
    out_dataset.SetProjection(projection)
    out_dataset = None
    out_band = None

    Sieve_filter(out_file, out_file2, 16)


if __name__ == "__main__":
    print("program run")
    start_time = time.time()

    in_file = r"E:\pingdingshan\L2A_T49SGS_T49SGT_T49SFT_T49SFU_20180612_pingdingshan.tif"
    out_file = r"E:\pingdingshan\L2A_T49SGS_T49SGT_T49SFT_T49SFU_20180612_pingdingshan_tmp.tif"
    out_file2 = r"E:\pingdingshan\L2A_T49SGS_T49SGT_T49SFT_T49SFU_20180612_pingdingshan_class.tif"

    # in_file = r"D:\Data\Test_data\out_s2_luoyang\Sub_ref\S2A_MSIL2A_20180725T031541_N0206_R118_T49SEU_20180725T061658\L2A_T49SEU_A016131_20180725T032152_ref_10m.tif"
    # out_file = r"D:\Data\Test_data\out_s2_luoyang\Sub_ref\S2A_MSIL2A_20180725T031541_N0206_R118_T49SEU_20180725T061658\L2A_T49SEU_A016131_20180725T032152_ref_10m_class2.tif"
    # out_file2 = r"D:\Data\Test_data\out_s2_luoyang\Sub_ref\S2A_MSIL2A_20180725T031541_N0206_R118_T49SEU_20180725T061658\L2A_T49SEU_A016131_20180725T032152_ref_10m_class3_ss.tif"
    # in_file = r"D:\Data\Test_data\out_s2_luoyang\Sub_ref\S2A_MSIL2A_20180725T031541_N0206_R118_T49SET_20180725T061658\L2A_T49SET_A016131_20180725T032152_ref_10m.tif"
    # out_file = r"D:\Data\Test_data\out_s2_luoyang\Sub_ref\S2A_MSIL2A_20180725T031541_N0206_R118_T49SET_20180725T061658\L2A_T49SET_A016131_20180725T032152_ref_10m_temp.tif"
    # out_file2 = r"D:\Data\Test_data\out_s2_luoyang\Sub_ref\S2A_MSIL2A_20180725T031541_N0206_R118_T49SET_20180725T061658\L2A_T49SET_A016131_20180725T032152_ref_10m_class2.tif"
    #
    # in_file = r"D:\Data\Test_data\out_s2_luoyang\Sub_ref\S2A_MSIL2A_20180725T031541_N0206_R118_T49SFT_20180725T061658\L2A_T49SFT_A016131_20180725T032152_ref_10m.tif"
    # out_file = r"D:\Data\Test_data\out_s2_luoyang\Sub_ref\S2A_MSIL2A_20180725T031541_N0206_R118_T49SFT_20180725T061658\L2A_T49SFT_A016131_20180725T032152_ref_10m_temp.tif"
    # out_file2 = r"D:\Data\Test_data\out_s2_luoyang\Sub_ref\S2A_MSIL2A_20180725T031541_N0206_R118_T49SFT_20180725T061658\L2A_T49SFT_A016131_20180725T032152_ref_10m_class2.tif"

    # in_file  = r"D:\Data\Test_data\out_s2_luoyang\Sub_ref\S2A_MSIL2A_20180725T031541_N0206_R118_T49SFU_20180725T061658\L2A_T49SFU_A016131_20180725T032152_ref_10m.tif"
    # out_file = r"D:\Data\Test_data\out_s2_luoyang\Sub_ref\S2A_MSIL2A_20180725T031541_N0206_R118_T49SFU_20180725T061658\L2A_T49SFU_A016131_20180725T032152_ref_10m_temp.tif"
    # out_file2 = r"D:\Data\Test_data\out_s2_luoyang\Sub_ref\S2A_MSIL2A_20180725T031541_N0206_R118_T49SFU_20180725T061658\L2A_T49SFU_A016131_20180725T032152_ref_10m_class2.tif"

    main(in_file, out_file)
    # if len(sys.argv[1:]) == 3:
    #     nir_pos,red_pos = str(sys.argv[3]).split(',')
    # if len(sys.argv[1:]) == 2:
    #     nir_pos, red_pos = '4','3'
    # if len(sys.argv[1:]) < 2:
    #     sys.exit('Problem reading input')
    # main(sys.argv[1], sys.argv[2])

    end_time = time.time()
    print('\n' + "time: %.2f min." % ((end_time - start_time) / 60))
