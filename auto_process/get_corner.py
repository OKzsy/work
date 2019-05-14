#!/usr/bin/env python3
# -*- coding:utf-8 -*-


import time


try:
    from osgeo import gdal, ogr, osr
except ImportError:
    import gdal, ogr, osr


def corner_to_geo(sample, line, dataset):
    """

    :param sample: 所计算点的列号
    :param line:   所计算点的行号
    :param dataset: 所计算影像的dataset
    :return: 所计算点的地理坐标
    """
    # 计算指定行,列号的地理坐标
    Geo_t = dataset.GetGeoTransform()
    # 计算地理坐标
    geoX = Geo_t[0] + sample * Geo_t[1]
    geoY = Geo_t[3] + line * Geo_t[5]
    return geoX, geoY


def corner(data_ds):
    """

    :param data_ds: 所计算影像的dataset
    :return: 转换为经纬度的角点地理坐标
    """
    # 定义目标投影
    oSRS = osr.SpatialReference()
    oSRS.SetWellKnownGeogCS("WGS84")

    # 获取原始投影
    src_prj = data_ds.GetProjection()
    oSRC = osr.SpatialReference()
    oSRC.ImportFromWkt(src_prj)
    # 测试投影转换
    oSRC.SetTOWGS84(0, 0, 0)
    tx = osr.CoordinateTransformation(oSRC, oSRS)

    # 获取原始影像的放射变换参数
    geo_t = data_ds.GetGeoTransform()
    x_size = data_ds.RasterXSize  # Raster xsize
    y_size = data_ds.RasterYSize  # Raster ysize
    bandCount = data_ds.RasterCount  # Band Count
    dataType = data_ds.GetRasterBand(1).DataType  # Data Type
    # 获取影像的四个角点地理坐标
    # 左上
    old_ulx, old_uly = corner_to_geo(0, 0, data_ds)
    # 右上
    old_urx, old_ury = corner_to_geo(x_size, 0, data_ds)
    # 左下
    old_dlx, old_dly = corner_to_geo(0, y_size, data_ds)
    # 右下
    old_drx, old_dry = corner_to_geo(x_size, y_size, data_ds)

    # 计算出转换后角点的坐标（经纬度）
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
    drx = max(new_urx, new_drx)
    # 右下纬度
    dry = min(new_dly, new_dry)
    # 右上经纬度
    urx = drx
    # 右上纬度
    ury = uly
    # 左下纬度
    dlx = ulx
    # 左下纬度
    dly = dry
    return {"topLeft": [ulx, uly],
            "topRight": [urx, ury],
            "downLeft": [dlx, dly],
            "downRight": [drx, dry]}


def main(**keywords):
    # 注册所有gdal的驱动
    gdal.AllRegister()
    gdal.SetConfigOption("gdal_FILENAME_IS_UTF8", "YES")
    # 获取参数
    img = keywords['img']
    # 打开影像
    img_ds = gdal.Open(img)
    # 开始计算角点
    points = corner(data_ds=img_ds)

    return None


if __name__ == '__main__':
    start_time = time.clock()
    in_file = r""
    main(img=in_file)
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))
