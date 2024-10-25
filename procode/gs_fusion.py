#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2019/1/8 10:47

Description:
    基于全色波段和多光谱影像（两景影像行列数必须一致），利用GS融合算法，生成融合影像

Parameters
    参数1：输入全色影像路径
    参数2：输入多光谱影像路径
    参数3：输出融合后影像路径

"""

import os
import gc
import sys
import time
import numpy as np
from sys import getrefcount
import matplotlib.pyplot as plt

try:
    from osgeo import gdal, ogr
except ImportError:
    import gdal, ogr

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def Tif_read(in_file):
    source_dataset = gdal.Open(in_file)
    if source_dataset is None:
        sys.exit('Problem opening file %s !' % in_file)

    xsize = source_dataset.RasterXSize
    ysize = source_dataset.RasterYSize
    geotransform = source_dataset.GetGeoTransform()
    projection = source_dataset.GetProjectionRef()
    in_band = source_dataset.GetRasterBand(1)
    data = source_dataset.ReadAsArray(0, 0, xsize, ysize)
    source_dataset = None

    return data, in_band, geotransform, projection


def writeTiff(im_data, im_width, im_height, im_bands, im_geotrans, im_proj, path):
    if 'int8' in im_data.dtype.name:
        datatype = gdal.GDT_Byte
    elif 'int16' in im_data.dtype.name:
        datatype = gdal.GDT_UInt16
    else:
        datatype = gdal.GDT_Float32

    if len(im_data.shape) == 3:
        im_bands, im_height, im_width = im_data.shape
    elif len(im_data.shape) == 2:
        im_data = np.array([im_data])
    else:
        im_bands, (im_height, im_width) = 1, im_data.shape
        # 创建文件
    driver = gdal.GetDriverByName("GTiff")
    dataset = driver.Create(path, im_width, im_height, im_bands, datatype)
    if (dataset != None):
        dataset.SetGeoTransform(im_geotrans)  # 写入仿射变换参数
        dataset.SetProjection(im_proj)  # 写入投影
    for i in range(im_bands):
        dataset.GetRasterBand(i + 1).WriteArray(im_data[i])
    del dataset


def cdf(img):
    hist, bins = np.histogram(img.flatten(), 256, [0, 256])
    cdf = hist.cumsum()
    cdf_normalized = cdf * float(hist.max()) / cdf.max()
    cdf_unit = cdf / cdf.max()
    plt.plot(cdf_normalized, color='b')
    plt.hist(img.flatten(), 256, [0, 256], color='r')
    plt.xlim([0, 256])
    plt.legend(('cdf', 'histogram'), loc='upper left')
    plt.show()
    return cdf_unit, hist


# def sigma(B):#标准差
#    c,r=B.shape
#    sigma=np.sqrt((B-np.mean(B))**2/c*r)
#    return sigma

def var(B):  # 方差
    n = B.shape[0]
    var = np.sum(((B - np.mean(B)) ** 2), dtype=np.float64) / n
    return var


def cov(X, Y):  # A,B为向量，协方差
    cov = np.sum((X - np.mean(X)) * (Y - np.mean(Y))) / X.shape[0]
    return cov


def phi(X, Y):
    phi = cov(X, Y) / var(Y)
    return phi


def GS(B):  # (M*N,4)
    GS = np.zeros(B.shape)
    for i in range(B.shape[1]):
        print(i)
        if i == 0:
            GS[:, 0] = B[:, 0]  # GS第一分量不变
        else:
            for j in range(0, i):
                if j == 0:
                    phi_GS = phi(B[:, i], GS[:, 0]) * GS[:, 0]

                else:
                    phi_GS += phi(B[:, i], GS[:, j]) * GS[:, j]
                    continue
                print(phi(B[:, i], GS[:, j]))
            print(phi_GS)
            GS[:, i] = B[:, i] - np.mean(B[:, i]) - phi_GS
            phi_GS = None
            continue
    return GS


def GS_inverse(GS, B):
    B_t = np.zeros(GS.shape)
    for i in range(GS.shape[1]):
        print(i)
        if i == 0:
            B_t[:, 0] = GS[:, 0]  # GS第一分量不变
        else:
            for j in range(0, i):
                if j == 0:
                    phi_GS = phi(B[:, i], GS[:, 0]) * GS[:, 0]
                    # print(j,i-1)

                # print(phi(B[:,i],GS[:,j]),j,i-1)
                else:
                    phi_GS += phi(B[:, i], GS[:, j]) * GS[:, j]
                    print(phi(B[:, i], GS[:, j]))
                    continue
            B_t[:, i] = GS[:, i] + np.mean(B[:, i]) + phi_GS
            print(phi_GS)
            phi_GS = None
            continue
    return B_t


def histogram_match(img1, img3):
    cdf1, hist1 = cdf(img1)
    cdf3, hist3 = cdf(img3)
    map = [0] * cdf1.shape[0]
    for i in range(cdf1.shape[0]):
        for j in range(1, cdf3.shape[0]):
            if hist1[i] != 0:

                if np.abs(cdf1[i] - cdf3[j]) <= np.abs(cdf1[i] - cdf3[j - 1]):
                    map[i] = j
                    continue
                else:
                    break
            else:
                map[i] = i
    return map, hist1, hist3


def modify_pan_hist(img1, img3):
    map, hist1, hist3 = histogram_match(img1, img3)
    img4 = np.zeros(img1.shape)
    img4[:, :] = img1[:, :]
    for i in range(256):
        img4[np.where(img4 == i)] = map[i]
    return img4


def modify_pan_stat(img1, img3):  # 拉伸img1，使其具有跟img3相似的分辨率
    mu3 = np.mean(img3)
    mu1 = np.mean(img1)
    sigma3 = np.sqrt(var(img3))
    sigma1 = np.sqrt(var(img1))
    gain = sigma3 / sigma1  # 增益
    print(gain)
    bias = mu3 - (gain * mu1)  # 偏移
    print(bias)
    M_P = img1 * gain + bias
    return M_P


def resize_tif(pan, mss):
    # 打开高分辨率影像
    pan_ds = gdal.Open(pan)
    pan_xsize = pan_ds.RasterXSize
    pan_ysize = pan_ds.RasterYSize
    pan_geo = pan_ds.GetGeoTransform()
    # 打开低分辨率影像
    mss_ds = gdal.Open(mss)
    mss_prj = mss_ds.GetProjection()
    mss_geo = mss_ds.GetGeoTransform()
    mss_xsize = mss_ds.RasterXSize
    mss_ysize = mss_ds.RasterYSize
    bandCount = mss_ds.RasterCount  # Band Count
    dataType = mss_ds.GetRasterBand(1).DataType  # Data Type
    # 判断输入影像是否正确
    if pan_geo[1] > mss_geo[1]:
        sys.exit("The order of input files is wrongT!")
    # 计算输出后影像的分辨率
    # 计算缩放系数
    fact = np.array([pan_xsize / mss_xsize, pan_ysize / mss_ysize])
    xs = mss_geo[1] / fact[0]
    ys = mss_geo[5] / fact[1]
    # 创建输出影像
    out_driver = gdal.GetDriverByName("MEM")
    out_ds = out_driver.Create('', pan_xsize, pan_ysize, bandCount, dataType)
    out_ds.SetProjection(mss_prj)
    out_geo = list(mss_geo)
    out_geo[1] = xs
    out_geo[5] = ys
    out_ds.SetGeoTransform(out_geo)
    # 执行重投影和重采样
    print('Begin to reprojection and resample!')
    res = gdal.ReprojectImage(mss_ds, out_ds, \
                              mss_prj, mss_prj, \
                              gdal.GRA_Bilinear, callback=progress)
    data = out_ds.ReadAsArray()
    in_band = out_ds.GetRasterBand(1)
    geotransform = out_ds.GetGeoTransform()
    projection = out_ds.GetProjection()
    pan_ds = None
    mss_ds = None
    out_ds = None
    return data, in_band, geotransform, projection


def main(in_file1, in_file2, out_file):
    data1, in_band1, geotransform1, projection1 = Tif_read(in_file1)
    data2, in_band2, geotransform2, projection2 = resize_tif(in_file1, in_file2)
    img1 = data1  # 高分辨率全色影像
    del data1
    gc.collect()
    img2 = data2.transpose(1, 2, 0)  # 低分辨率多光谱影像
    del data2
    gc.collect()
    img3 = np.mean(img2, axis=2, dtype='float16')  # img3为模拟的低分辨率全色影像#用多光谱各波段均值来模拟
    #    cdf(img1)
    #    cdf(img3)
    #    img1=np.int32(img1)
    #    img3=np.int32(img3)
    B2 = img2.reshape(img2.shape[0] * img2.shape[1], img2.shape[2])
    B3 = img3.ravel()
    B = np.c_[B3, B2].astype("float16")
    del B3, B2
    gc.collect()
    gs = GS(B)
    #    img4=modify_pan_hist(img1,img3)
    img4 = modify_pan_stat(img1, img3)
    del img3
    gs[:, 0] = img4.ravel()
    B_t = GS_inverse(gs, B)
    new = B_t.reshape(img1.shape[0], img2.shape[1], B.shape[-1])[:, :, 1:]
    # new_gs=gs.reshape(img1.shape[0],img1.shape[1],B.shape[-1])[:,:,1:]
    h = np.zeros_like(new)
    for i in range(new.shape[2]):
        h = new[:, :, i]
        new[:, :, i] = h - np.mean(h) + np.mean(img2[:, :, i])
    new = new.transpose(2, 0, 1)
    channel, xsize, ysize = new.shape
    writeTiff(new, ysize, xsize, channel, geotransform1, projection1, out_file)
    # return img1, img2, img3, img4, B_t, B


if __name__ == '__main__':
    start_time = time.time()

    # if len(sys.argv[1:]) < 3:
    #     sys.exit('Problem reading input')
    # in_file1 = r"F:\GF\GF2_PMS2_E113.1_N34.9_20171020_L1A0002693345-PAN2.tif"
    # in_file2 = r"F:\GF\GF2_PMS2_E113.1_N34.9_20171020_L1A0002693345-MSS2.tif"
    in_file1 = r"F:\test_data\GS_test\5952_pan.tif"
    in_file2 = r"F:\test_data\GS_test\5952_MSS.tif"
    out_file = r"F:\test_data\GS_test\test.tif"

    # in_file1 = sys.argv[1]
    # in_file2 = sys.argv[2]
    # out_file = sys.argv[3]

    main(in_file1, in_file2, out_file)

    # img1, img2, img3, img4, B_t, B = main(in_file1, in_file2, out_file)

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))
