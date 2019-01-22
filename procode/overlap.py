#!/usr/bin/env python
# -*- coding:utf-8 -*-

from osgeo import gdal, ogr, gdalconst
import time
import sys


def Corner_coordinates(dataset):
    # 获取原始影像的放射变换参数
    geo_t = dataset.GetGeoTransform()
    x_size = dataset.RasterXSize  # Raster xsize
    y_size = dataset.RasterYSize  # Raster ysize
    # 获取影像的四个角点地理坐标
    # 左上
    old_ulx, old_uly = gdal.ApplyGeoTransform(geo_t, 0, 0)
    # 右上
    old_urx, old_ury = gdal.ApplyGeoTransform(geo_t, x_size, 0)
    # 左下
    old_dlx, old_dly = gdal.ApplyGeoTransform(geo_t, 0, y_size)
    # 右下
    old_drx, old_dry = gdal.ApplyGeoTransform(geo_t, x_size, y_size)

    return [old_ulx, old_uly, old_urx, old_ury, old_dlx, old_dly, old_drx, old_dry]


def main(infile1, infile2):
    src_ds = gdal.Open(infile1)
    mask_ds = gdal.Open(infile2)
    # 获取影像的投影和转换参数
    src_geo = src_ds.GetGeoTransform()
    mask_geo = mask_ds.GetGeoTransform()
    # 获取影像的四角坐标
    src_corner = Corner_coordinates(src_ds)
    mask_corner = Corner_coordinates(mask_ds)
    # 获取逆仿射变换的参数
    mask_inv_geo = gdal.InvGeoTransform(mask_geo)
    offset_ul = gdal.ApplyGeoTransform(mask_inv_geo, src_corner[0], src_corner[1])
    offset_dr = gdal.ApplyGeoTransform(mask_inv_geo, src_corner[6], src_corner[7])
    off_ulx, off_uly = map(int, offset_ul)
    off_drx, off_dry = map(int, offset_dr)
    # 获取被检测影像的行列数
    x_size = mask_ds.RasterXSize  # Raster xsize
    y_size = mask_ds.RasterYSize  # Raster ysize
    # 判断影像是否有重叠区域
    if off_ulx >= x_size or off_uly >= y_size or off_drx <= 0 or off_dry <= 0:
        sys.exit("Have no overlap")
    # 计算重叠区域的四角坐标
    # 左上
    ulx = max(src_corner[0], mask_corner[0])
    uly = min(src_corner[1], mask_corner[1])
    # 右上
    urx = min(src_corner[2], mask_corner[2])
    ury = min(src_corner[3], mask_corner[3])
    # 左下
    dlx = max(src_corner[4], mask_corner[4])
    dly = max(src_corner[5], mask_corner[5])
    # 右下
    drx = min(src_corner[6], mask_corner[6])
    dry = max(src_corner[7], mask_corner[7])
    # 根据经纬度范围分别获取重叠区域在两幅影像中的行列号
    # src
    # 获取逆放射变换参数
    src_inv_geo = gdal.InvGeoTransform(src_geo)
    # 计算行列号
    # 左上
    src_off_ulx, src_off_uly = map(int, gdal.ApplyGeoTransform(src_inv_geo, ulx, uly))
    # 右上
    src_off_urx, src_off_ury = map(int, gdal.ApplyGeoTransform(src_inv_geo, urx, ury))
    # 左下
    src_off_dlx, src_off_dly = map(int, gdal.ApplyGeoTransform(src_inv_geo, dlx, dly))
    # 右下
    src_off_drx, src_off_dry = map(int, gdal.ApplyGeoTransform(src_inv_geo, drx, dry))
    # 获取最小矩形的左上角和右下角行列号
    # 左上
    src_offset_ulx = min(src_off_ulx, src_off_dlx)
    src_offset_uly = min(src_off_uly, src_off_ury)
    # 右下
    src_offset_drx = max(src_off_urx, src_off_drx)
    src_offset_dry = max(src_off_dly, src_off_dry)
    # mask
    # 计算行列号
    # 左上
    mask_off_ulx, mask_off_uly = map(int, gdal.ApplyGeoTransform(mask_inv_geo, ulx, uly))
    # 右上
    mask_off_urx, mask_off_ury = map(int, gdal.ApplyGeoTransform(mask_inv_geo, urx, ury))
    # 左下
    mask_off_dlx, mask_off_dly = map(int, gdal.ApplyGeoTransform(mask_inv_geo, dlx, dly))
    # 右下
    mask_off_drx, mask_off_dry = map(int, gdal.ApplyGeoTransform(mask_inv_geo, drx, dry))
    # 获取最小矩形的左上角和右下角行列号
    # 左上
    mask_offset_ulx = min(mask_off_ulx, mask_off_dlx)
    mask_offset_uly = min(mask_off_uly, mask_off_ury)
    # 右下
    mask_offset_drx = max(mask_off_urx, mask_off_drx)
    mask_offset_dry = max(mask_off_dly, mask_off_dry)

    print(infile1)
    print(infile2)

    return None


if __name__ == '__main__':
    # 注册所有gdal的驱动
    gdal.AllRegister()
    gdal.SetConfigOption("gdal_FILENAME_IS_UTF8", "YES")
    startTime = time.clock()

    file1 = r"F:\test_data\clipraster\SatImage.tif"
    # file2 = r"F:\test_data\clipraster\SatImage.tif"
    file2 = r"F:\test_data\clipraster\gdal_mask2\test3_mask1.tif"
    main(file1, file2)

    endTime = time.clock()
    print("time: %.4f secs." % (endTime - startTime))
