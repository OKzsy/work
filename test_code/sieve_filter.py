#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May 31 15:50:24 2018

@author: 01
"""
import time

try:
    from osgeo import gdal
except ImportError:
    import gdal
import os
import numpy as np
import sys


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
    # out_band.SetNoDataValue(0)
    out_dataset.SetGeoTransform(geotransform)
    out_dataset.SetProjection(projection)
    source_dataset = None
    out_dataset = None
    # return out_file


#     # 进度条
#     # bar_value = int(60 - 1)
#     # str = '>' * (bar_value // 2) + ' ' * ((100 - bar_value) // 2)
#     # sys.stdout.write('\r' + str + '[%s%%]' % (bar_value + 1))
def main(in_file, out_file, size):
    Sieve_filter(in_file, out_file, 2 ** size)


if __name__ == '__main__':
    start = time.time()
    in_file = r"F:\Sub_ref\luoyang_S2_2.tif"
    out_file = r"F:\Sub_ref\luoyang_S2_sieve.tif"
    size = 6
    main(in_file, out_file, size)
    # main(sys.argv[1],sys.argv[2],int(sys.argv[3]))
    end = time.time()
    print(end - start)
