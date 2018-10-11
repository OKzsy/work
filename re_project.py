#!/usr/bin/env python
# -*- coding:utf-8 -*-

try:
    from osgeo import gdal, gdalconst, osr
except ImportError:
    import gdal, gdalconst, osr
try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def reprojectRaster(src, match_ds, dst_filename):
    src_proj = src.GetProjection()
    src_geotrans = src.GetGeoTransform()
    src_band = src.RasterCount

    match_proj = match_ds.GetProjection()
    match_geotrans = match_ds.GetGeoTransform()
    wide = match_ds.RasterXSize
    high = match_ds.RasterYSize

    dst = gdal.GetDriverByName('GTiff').Create(dst_filename, wide, high, src_band, gdalconst.GDT_Int16)
    dst.SetGeoTransform(match_geotrans)
    dst.SetProjection(match_proj)

    gdal.ReprojectImage(src, dst, src_proj, match_proj, gdalconst.GRA_NearestNeighbour)

    del dst  # Flush
    return (gdal.Open(dst_filename, gdalconst.GA_ReadOnly))


def main(in_file, match_file, out_file):
    src = gdal.Open(in_file)
    match_ds = gdal.Open(match_file)
    dst_filename = out_file
    reprojectRaster(src, match_ds, dst_filename)


if __name__ == '__main__':
    print('program running')

    in_file = r"G:\20180823\yuanshi\L2A_yingqiao_20180523_clip.tif"
    match_file = r"G:\20180823\yuanshi\GF2_Pan_yingqiao_clip.tif"
    out_file = r"G:\20180823\yuanshi\GF2_Pan_yingqiao_resample.tif"
    main(in_file, match_file, out_file)
