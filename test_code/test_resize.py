#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import glob
from osgeo import gdal
import numpy as np
import time


def get_indices(source_ds, target_width, target_height):
    """根据旧像素获取新像素偏移的函数

    source_ds -dataset to get offsets from
    target_width -target pixel width
    target_width -target pixel height (negative)
    """
    source_geotransform = source_ds.GetGeoTransform()
    source_width = source_geotransform[1]
    source_height = source_geotransform[5]

    dx = target_width / source_width
    dy = target_height / source_height
    target_x = np.arange(dx / 2, source_ds.RasterXSize, dx)
    target_y = np.arange(dy / 2, source_ds.RasterYSize, dy)
    return np.meshgrid(target_x, target_y)


def bilinear(in_data, x, y):
    """

    :param in_data: - the input dataset to be resample
    :param x: - an array of x coordinates for output pixel centers
    :param y: - an array of x coordinates for output pixel centers
    :return:  - the resampled result
    """
    # x -= 0.5
    # y -= 0.5
    nb, rows, cols = in_data.shape
    x0 = np.floor(x).astype(int)
    x11 = x0 + 1
    x1 = np.minimum(x11, cols - 1)
    y0 = np.floor(y).astype(int)
    y11 = y0 + 1
    y1 = np.minimum(y11, rows - 1)

    ul = in_data[:, y0, x0] * (y11 - y) * (x11 - x)
    ur = in_data[:, y0, x1] * (y11 - y) * (x - x0)
    ll = in_data[:, y1, x0] * (y - y0) * (x11 - x)
    lr = in_data[:, y1, x1] * (y - y0) * (x - x0)

    return ul + ur + ll + lr


if __name__ == '__main__':
    start_time = time.clock()
    in_fn = r'F:\cailanzi\test_mos\20181119_024124_101b\20181119_024124_101b_3B_AnalyticMS_SR.tif'
    out_fn = r'F:\cailanzi\test_mos\20181119_024124_101b\20181119_024124_101b_3B_AnalyticMS_SR_bilinear_py.tif'

    # source_dataset = gdal.Open(in_fn)
    #
    #
    # # 获取数据基本信息
    # xsize = source_dataset.RasterXSize
    # ysize = source_dataset.RasterYSize
    # num_band = source_dataset.RasterCount
    # data_type = source_dataset.GetRasterBand(1).DataType
    #
    # in_geo = source_dataset.GetGeoTransform()
    # in_proj = source_dataset.GetProjectionRef()
    #
    #
    # # output geotiff file
    # out_driver = gdal.GetDriverByName('GTiff')
    # if os.path.exists(out_fn):
    #     out_driver.Delete(out_fn)
    #
    # # warpMemoryLimit= 4096,
    # gdal.Warp(out_fn, in_fn, format='GTiff',
    #           srcSRS=in_proj, dstSRS=in_proj,
    #           multithread=True,
    #           resampleAlg=gdal.GRA_Bilinear,
    #           xRes=1.5, yRes=1.5)

    # cell_size = (12.0, -12.0)
    # in_ds = gdal.Open(in_fn)
    # x, y = get_indices(in_ds, *cell_size)
    #
    # # new_data = in_ds.ReadAsArray()[y.astype(int), x.astype(int)]
    # new_data = in_ds.ReadAsArray()[:, y.astype(int), x.astype(int)]
    # # new_data = in_ds.ReadAsArray(500,0,4,4)
    #
    # gtiff_driver = gdal.GetDriverByName('GTiff')
    # nb, rows, columns = new_data.shape
    # out_ds = gtiff_driver.Create(
    #     out_fn, columns, rows, nb, gdal.GDT_UInt16)
    # out_ds.SetProjection(in_ds.GetProjection())
    #
    # gt = list(in_ds.GetGeoTransform())
    # gt[1] = cell_size[0]
    # gt[5] = cell_size[1]
    # out_ds.SetGeoTransform(gt)
    # for band in range(1, nb):
    #     out_band = out_ds.GetRasterBand(band)
    #     out_band.WriteArray(new_data[band - 1, :, :])
    #
    # out_band.FlushCache()
    # del out_ds
    # del in_ds

    cell_size = (1.5, -1.5)
    in_ds = gdal.Open(in_fn)
    x, y = get_indices(in_ds, *cell_size)

    new_data = bilinear(in_ds.ReadAsArray(), x, y)
    gtiff_driver = gdal.GetDriverByName('GTiff')
    nb, rows, columns = new_data.shape
    out_ds = gtiff_driver.Create(
        out_fn, columns, rows, nb, gdal.GDT_Int32)
    out_ds.SetProjection(in_ds.GetProjection())

    gt = list(in_ds.GetGeoTransform())
    gt[1] = cell_size[0]
    gt[5] = cell_size[1]
    out_ds.SetGeoTransform(gt)
    for band in range(1, nb):
        out_band = out_ds.GetRasterBand(band)
        out_band.WriteArray(new_data[band - 1, :, :])

    out_band.FlushCache()
    del out_ds
    del in_ds
    end_time = time.clock()
    print("time: %.4f secs." % (end_time - start_time))
