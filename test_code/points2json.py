#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/5/18 15:47
# @Author  : zhaoss
# @FileName: points2json.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""
import os
import glob
import time
import json
import base64
import numpy as np
import xml.dom.minidom as xml_mini
from osgeo import gdal, ogr, osr, gdalconst
from ospybook.vectorplotter import VectorPlotter

import os
try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def rpj_vec(lyr, srs):
    """对矢量进行投影变换"""
    # 创建临时矢量文件
    mem_dri = ogr.GetDriverByName('Memory')
    mem_ds = mem_dri.CreateDataSource(' ')
    outLayer = mem_ds.CreateLayer(' ', geom_type=lyr.GetGeomType(), srs=srs)
    # 附加字段
    outLayer.CreateFields(lyr.schema)
    # 逐要素进行投影转换
    out_feat = ogr.Feature(outLayer.GetLayerDefn())
    for in_feat in lyr:
        geom = in_feat.geometry().Clone()
        geom.TransformTo(srs)
        out_feat.SetGeometry(geom)
        # 写入属性信息
        for i in range(in_feat.GetFieldCount()):
            out_feat.SetField(i, in_feat.GetField(i))
        outLayer.CreateFeature(out_feat)
    return mem_ds, outLayer


def sample_xml_change():
    return None


def Feature_memory_shp(feat, sr):
    """将指定的geometry导出为内存中单独的shpfile"""
    fid = feat.GetFID()
    # 在内存中创建临时的矢量文件，用以存储单独的要素
    # 创建临时矢量文件
    mem_dri = ogr.GetDriverByName('Memory')
    mem_ds = mem_dri.CreateDataSource(' ')
    outLayer = mem_ds.CreateLayer(' ', geom_type=ogr.wkbPolygon, srs=sr)
    # 给图层中创建字段用以标识原来的FID
    coor_fld = ogr.FieldDefn('ID_FID', ogr.OFTInteger)
    outLayer.CreateField(coor_fld)
    # 创建虚拟要素，用以填充原始要素
    out_defn = outLayer.GetLayerDefn()
    out_feat = ogr.Feature(out_defn)
    # 对ID_FID字段填充值
    fld_index = outLayer.GetLayerDefn().GetFieldIndex('ID_FID')
    out_feat.SetField(fld_index, fid)
    # 填充要素
    out_feat.SetGeometry(feat.geometry())
    outLayer.CreateFeature(out_feat)
    return mem_ds, outLayer


def min_rect(raster_ds, shp_layer):
    # 获取栅格的大小
    x_size = raster_ds.RasterXSize
    y_size = raster_ds.RasterYSize
    # 获取是矢量的范围
    extent = shp_layer.GetExtent()
    # 获取栅格的放射变换参数
    raster_geo = raster_ds.GetGeoTransform()
    # 计算逆放射变换系数
    raster_inv_geo = gdal.InvGeoTransform(raster_geo)
    # 计算在raster上的行列号
    # 左上
    off_ulx, off_uly = map(round, gdal.ApplyGeoTransform(raster_inv_geo, extent[0], extent[3]))
    # 右下
    off_drx, off_dry = map(round, gdal.ApplyGeoTransform(raster_inv_geo, extent[1], extent[2]))
    # 判断是否有重叠区域
    if off_ulx >= x_size or off_uly >= y_size or off_drx <= 0 or off_dry <= 0:
        return 0
    # 限定重叠范围在栅格影像上
    # 列
    offset_column = np.array([off_ulx, off_drx])
    offset_column = np.maximum((np.minimum(offset_column, x_size - 1)), 0)
    # 行
    offset_line = np.array([off_uly, off_dry])
    offset_line = np.maximum((np.minimum(offset_line, y_size - 1)), 0)

    return [offset_column[0], offset_line[0], offset_column[1], offset_line[1]]


def shp2raster(raster_ds, shp_layer, ext):
    # 将行列整数浮点化
    ext = np.array(ext) * 1.0
    # 获取栅格数据的基本信息
    raster_prj = raster_ds.GetProjection()
    raster_geo = raster_ds.GetGeoTransform()
    # 根据最小重叠矩形的范围进行矢量栅格化
    ulx, uly = gdal.ApplyGeoTransform(raster_geo, ext[0], ext[1])
    x_size = ext[2] - ext[0]
    y_size = ext[3] - ext[1]
    # 创建mask
    # out = r"F:\test_data\clipraster\gdal_mask2\test3.tif"
    # mask_ds = gdal.GetDriverByName('GTiff').Create(out, int(x_size), int(y_size), 1, gdal.GDT_Byte)
    mask_ds = gdal.GetDriverByName('MEM').Create('', int(x_size), int(y_size), 1, gdal.GDT_Byte)
    mask_ds.SetProjection(raster_prj)
    mask_geo = [ulx, raster_geo[1], 0, uly, 0, raster_geo[5]]
    mask_ds.SetGeoTransform(mask_geo)
    # 矢量栅格化
    gdal.RasterizeLayer(mask_ds, [1], shp_layer, burn_values=[1])
    return mask_ds


def mask_raster(raster_ds, mask_ds, outfile, ext):
    # 将行列整数浮点化
    ext = np.array(ext) * 1.0
    # 获取栅格数据的基本信息
    raster_prj = raster_ds.GetProjection()
    raster_geo = raster_ds.GetGeoTransform()
    bandCount = 3
    dataType = raster_ds.GetRasterBand(1).DataType
    # 根据最小重叠矩形的范围进行矢量栅格化
    ulx, uly = gdal.ApplyGeoTransform(raster_geo, ext[0], ext[1])
    x_size = ext[2] - ext[0]
    y_size = ext[3] - ext[1]
    # 创建输出影像
    result_ds = gdal.GetDriverByName('GTiff').Create(outfile, int(x_size), int(y_size), bandCount, dataType)
    result_ds.SetProjection(raster_prj)
    result_geo = [ulx, raster_geo[1], 0, uly, 0, raster_geo[5]]
    result_ds.SetGeoTransform(result_geo)
    # 获取掩模
    mask = mask_ds.GetRasterBand(1).ReadAsArray()
    mask = 1 - mask
    # 对原始影像进行掩模并输出
    for band in range(bandCount):
        banddata = raster_ds.GetRasterBand(band + 1).ReadAsArray(int(ext[0]), int(ext[1]), int(x_size), int(y_size))
        banddata = np.choose(mask, (banddata, 0))
        result_ds.GetRasterBand(band + 1).WriteArray(banddata)
    result_ds.FlushCache()
    return 1


def add_child(dom, parent, tag, text=None):
    parent_tag = dom.getElementsByTagName(parent)[0]
    child = dom.createElement(tag)
    if text == None:
        parent_tag.appendChild(child)
    else:
        child.appendChild(dom.createTextNode(text))
        parent_tag.appendChild(child)
    return dom


def add_sample(dom, keywords):
    # 增加sample
    dom = add_child(dom, "annotation", "folder", keywords["folder"])
    dom = add_child(dom, "annotation", "filename", keywords["filename"])
    dom = add_child(dom, "annotation", "path", keywords["path"])
    dom = add_child(dom, "annotation", "source")
    dom = add_child(dom, "source", "database", keywords["database"])
    dom = add_child(dom, "annotation", "size")
    dom = add_child(dom, "size", "width", keywords["width"])
    dom = add_child(dom, "size", "height", keywords["height"])
    dom = add_child(dom, "size", "depth", keywords["depth"])
    dom = add_child(dom, "annotation", "segmented", keywords["segmented"])
    return dom


def add_label(dom, keywords):
    # 增加label
    # 获取根节点
    root_tag = dom.documentElement
    object_tag = dom.createElement("object")
    root_tag.appendChild(object_tag)

    name_tag = dom.createElement("name")
    name_tag.appendChild(dom.createTextNode(keywords["name"]))
    object_tag.appendChild(name_tag)

    pose_tag = dom.createElement("pose")
    pose_tag.appendChild(dom.createTextNode(keywords["pose"]))
    object_tag.appendChild(pose_tag)

    truncated_tag = dom.createElement("truncated")
    truncated_tag.appendChild(dom.createTextNode(keywords["truncated"]))
    object_tag.appendChild(truncated_tag)

    difficult_tag = dom.createElement("difficult")
    difficult_tag.appendChild(dom.createTextNode(keywords["difficult"]))
    object_tag.appendChild(difficult_tag)

    bndbox_tag = dom.createElement("bndbox")
    object_tag.appendChild(bndbox_tag)

    xmin_tag = dom.createElement("xmin")
    xmin_tag.appendChild(dom.createTextNode(keywords["xmin"]))
    bndbox_tag.appendChild(xmin_tag)

    ymin_tag = dom.createElement("ymin")
    ymin_tag.appendChild(dom.createTextNode(keywords["ymin"]))
    bndbox_tag.appendChild(ymin_tag)

    xmax_tag = dom.createElement("xmax")
    xmax_tag.appendChild(dom.createTextNode(keywords["xmax"]))
    bndbox_tag.appendChild(xmax_tag)

    ymax_tag = dom.createElement("ymax")
    ymax_tag.appendChild(dom.createTextNode(keywords["ymax"]))
    bndbox_tag.appendChild(ymax_tag)

    return dom


def calculate_offset(sample_up_left_corner, points, resolution):
    offset_point = []
    for point in points:
        offset_x = int((point[0] - sample_up_left_corner[0]) / resolution[0])
        offset_y = int((point[1] - sample_up_left_corner[1]) / resolution[1])
        offset_point.append([offset_x, offset_y])
    return offset_point


def main(sample_shp, lable_shp, json_path, img, out):
    """

    :param sample_shp:
    :param lable_shp:
    :param json_path:
    :param img:
    :param out:
    :return:
    """
    # 支持中文路径
    gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
    # 支持中文属性字段
    gdal.SetConfigOption("SHAPE_ENCODING", "GBK")
    # 注册矢量驱动
    ogr.RegisterAll()
    # 注册GDAL驱动
    gdal.AllRegister()
    # 开始处理
    # 打开栅格和矢量影像
    raster_ds = gdal.Open(img)
    raster_srs_wkt = raster_ds.GetProjection()
    raster_srs = osr.SpatialReference()
    raster_srs.ImportFromWkt(raster_srs_wkt)
    res = [raster_ds.GetGeoTransform()[1], raster_ds.GetGeoTransform()[5]]
    # 打开sample矢量文件
    sample_shp_ds = ogr.Open(sample_shp)
    sample_lyr = sample_shp_ds.GetLayer(0)
    # 打开label矢量文件
    lable_shp_ds = ogr.Open(lable_shp)
    lable_lyr = lable_shp_ds.GetLayer(0)
    # 定义label名字字典
    label_name = {'0': {'1': "footbool", \
                        '2': "basketball", \
                        '3': "tennis", \
                        '4': "volleyball", \
                        '5': "badminton", \
                        '6': "ping_pong", \
                        '9': "other_field"}, \
                  '1': {'1': "parking"}, \
                  '2': {'1': "red_roof", \
                        '2': "blue_roof", \
                        '3': "gray_roof", \
                        '4': "white_roof", \
                        '5': "black_roof"}, \
                  '3': {'1': "industry"}, \
                  '4': {'1': "green_cqdjgd", \
                        '2': "black_cqdjgd", \
                        '3': "rubbish_cqdjgd", \
                        '4': "fwjzgd"}, \
                  '5': {'1': "open_pit"}, \
                  '6': {'1': "strip_pit"}}
    # 循环sample中的geometry图形进行处理
    # vp = VectorPlotter(False)
    sample_lyr.ResetReading()
    for feat in sample_lyr:
        # 裁剪图像块
        fieldName = "name"
        out_img_name = os.path.join(out, feat.GetField(fieldName) + '.tiff')
        # json路径
        json_name = os.path.join(json_path, feat.GetField(fieldName) + '.json')
        # 打开json文件
        fp = open(json_name, "w")
        # 创建信息字典
        infor_dic = {}
        infor_dic["version"] = "3.9.0"
        infor_dic["flags"] = {}
        # 要素提取为图层
        feat_ds, feat_lyr = Feature_memory_shp(feat, raster_srs)
        # 要素裁剪
        # 计算矢量和栅格的最小重叠矩形
        offset = min_rect(raster_ds, feat_lyr)
        # 矢量栅格化
        mask_ds = shp2raster(raster_ds, feat_lyr, offset)
        # 进行裁剪
        result = mask_raster(raster_ds, mask_ds, out_img_name, offset)
        # 获取几何要素的范围
        germany = feat.geometry().Clone()
        # 获取sample的左上角点
        sample_ul = [germany.GetEnvelope()[0], germany.GetEnvelope()[3]]
        lable_lyr.ResetReading()
        lable_lyr.SetSpatialFilter(germany)
        # 创建shape信息列表
        shape_dic = []
        for label_feat in lable_lyr:
            # 创建label字典
            label_dic = {}
            label_dic["label"] = label_name[label_feat.GetField("obj_lab_1")][label_feat.GetField("obj_lab_2")]
            label_dic["line_color"] = None
            label_dic["fill_color"] = None
            # 获取几何要素的坐标点
            geom_points = label_feat.geometry().GetBoundary().GetPoints()[:-1]
            # 计算偏移序列
            offset_list = calculate_offset(sample_ul, geom_points, res)
            label_dic["points"] = offset_list
            label_dic["shape_type"] = "polygon"
            shape_dic.append(label_dic)
        lable_lyr.SetSpatialFilter(None)
        infor_dic["shapes"] = shape_dic
        infor_dic["lineColor"] = [0, 255, 0, 128]
        infor_dic["fillColor"] = [255, 0, 0, 128]
        infor_dic["imagePath"] = out_img_name
        # infor_dic["imageData"] = str(result)
        infor_dic["imageHeight"] = str(offset[3] - offset[1])
        infor_dic["imageWidth"] = str(offset[2] - offset[0])
        json.dump(infor_dic, fp)
        fp.close()
        dom = None

if __name__ == '__main__':
    start_time = time.clock()
    in_sample_shp = r"\\192.168.0.234\nydsj\project\8.变化检测\7.object detection\2.label_arcgis\3.label\露天体育场\sample_2985952.shp"
    in_lable_shp = r"\\192.168.0.234\nydsj\project\8.变化检测\7.object detection\2.label_arcgis\3.label\露天体育场\label_2985952.shp"
    img_path = r"\\192.168.0.234\nydsj\project\8.变化检测\1.data\1.GF\3.sha\GF2_20180206_L1A0002985952_sha.tif"
    xml_path = r"F:\ChangeMonitoring\sample\test"
    img_out_dir = r"F:\ChangeMonitoring\sample\test\img_out"
    main(sample_shp=in_sample_shp, lable_shp=in_lable_shp, json_path=xml_path, img=img_path, out=img_out_dir)
    end_time = time.clock()

    print("time: %.4f secs." % (end_time - start_time))


