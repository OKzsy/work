# -*- coding: utf-8 -*-
"""
Created on 2019/04/11 13:20:27

@author: xzz
"""
import sys
import time
import numpy as np
#import matplotlib.pyplot as plt

import ctypes  
from ctypes import *

GSFusionlib = ctypes.cdll.LoadLibrary("./libGSFusion.so")

try:
    from osgeo import gdal
except ImportError:
    import gdal

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress

def Tif_read(in_file):
    source_dataset=gdal.Open(in_file)
    if source_dataset is None:
        sys.exit('Problem opening file %s !' %in_file)

    xsize=source_dataset.RasterXSize
    ysize=source_dataset.RasterYSize
    geotransform=source_dataset.GetGeoTransform()
    projection=source_dataset.GetProjectionRef()
    in_band=source_dataset.GetRasterBand(1)
    data = source_dataset.ReadAsArray(0, 0, xsize, ysize)
    #print(data.dtype)
    source_dataset=None
    
    return  data,in_band,geotransform,projection
def writeTiff(im_data,im_width,im_height,im_bands,im_geotrans,im_proj,path):
    if 'int8' in im_data.dtype.name:
        datatype = gdal.GDT_Byte
    elif 'int16' in im_data.dtype.name:
        datatype = gdal.GDT_UInt16
    else:
        datatype = gdal.GDT_Float32
        #print("run to here")
    #print(datatype)
    if len(im_data.shape) == 3:
        im_bands, im_height, im_width = im_data.shape
    elif len(im_data.shape) == 2:
        im_data = np.array([im_data])
    else:
        im_bands, (im_height, im_width) = 1,im_data.shape
        #创建文件
    driver = gdal.GetDriverByName("GTiff")
    dataset = driver.Create(path, im_width, im_height, im_bands, datatype)
    if(dataset!= None):
        dataset.SetGeoTransform(im_geotrans) #写入仿射变换参数
        dataset.SetProjection(im_proj) #写入投影
    for i in range(im_bands):
        dataset.GetRasterBand(i+1).WriteArray(im_data[i])
    del dataset

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
    #print('Begin to reprojection and resample!')
    res = gdal.ReprojectImage(mss_ds, out_ds, \
                              mss_prj, mss_prj, \
                              gdal.GRA_Bilinear, callback=progress)
    #print('reprojection end1')
    data = out_ds.ReadAsArray()
    in_band = out_ds.GetRasterBand(1)
    geotransform = out_ds.GetGeoTransform()
    projection = out_ds.GetProjection()
    pan_ds = None
    mss_ds = None
    out_ds = None
    return data, in_band, geotransform, projection    
    
def GS_Fusion_main(in_file1,in_file2,out_file):
    
    data1,in_band1,geotransform1,projection1=Tif_read(in_file1)
    data2,in_band2,geotransform2,projection2=resize_tif(in_file1, in_file2)#Tif_read(in_file2)
    if data1.shape[0] != data2.shape[1]:
        print("The image fusion algorithm requires that the input images must have the same resolution!")
        return
    if data1.shape[1] != data2.shape[2]:
        print("The image fusion algorithm requires that the input images must have the same resolution!")
        return
    height = data2.shape[1]#.astype(np.int32)
    width = data2.shape[2]#.astype(np.int32)
    channelNum1 = 1#data1.shape[0]
    channelNum2 = data2.shape[0]
    #print(channelNum1)
    #print(channelNum2)
    
    #start = time.time()
    #print(data1.ty)
    panchromaticImg=data1.astype(np.float32)#高分辨率全色影像
    multiSpectralImg=data2.astype(np.float32).reshape(data2.shape[0],data2.shape[1]*data2.shape[2])#低分辨率多光谱影像

    if not panchromaticImg.flags['C_CONTIGUOUS']:
        panchromaticImg = np.ascontiguous(panchromaticImg, dtype=panchromaticImg.dtype)
    panchromaticImg_ctypes_ptr = cast(panchromaticImg.ctypes.data, POINTER(c_float))#c_int
    if not multiSpectralImg.flags['C_CONTIGUOUS']:
        multiSpectralImg = np.ascontiguous(multiSpectralImg, dtype=multiSpectralImg.dtype)
    multiSpectralImg_ctypes_ptr = cast(multiSpectralImg.ctypes.data, POINTER(c_float))#c_int

    fusionImg=np.zeros(data2.shape, dtype=np.float32)
    if not fusionImg.flags['C_CONTIGUOUS']:
        fusionImg = np.ascontiguous(fusionImg, dtype=fusionImg.dtype)
    fusionImg_ctypes_ptr = cast(fusionImg.ctypes.data, POINTER(c_float))

    widthStep_1 = width * 4
    widthStep_2 = width * 4
    GSFusionlib.GS_Fusion(panchromaticImg_ctypes_ptr, channelNum1, multiSpectralImg_ctypes_ptr, channelNum2, width, height, widthStep_1, widthStep_2, fusionImg_ctypes_ptr)

    #print(multiSpectralImg.shape)
    #print(data2.shape)
    channel,xsize,ysize=fusionImg.shape
    
    #end = time.time()
    #print("耗时")
    #print(end - start) 
    
    writeTiff(fusionImg,ysize,xsize,channel,geotransform1,projection1,out_file)
    #return img1,img2,img3,img4,B_t,B
    
if __name__=='__main__':
      
      in_file1=r"GF2_PMS1_E112.9_N34.7_20171020_L1A0002693207-PAN1_ort-atm.tif"#"2.tif"#"E:\image_fusion\tian\GF2_20180327_PAN2_gdz_reg_clip.tif"
      in_file2=r"GF2_PMS1_E112.9_N34.7_20171020_L1A0002693207-MSS1_ort-atm.tif"#"3.tif"#"E:\image_fusion\tian\GF2_20180327_MSS2_gdz_reg_clip.tif"
      out_file=r"GS_python.tif" 

      #img1,img2,img3,img4,B_t,B=main(in_file1,in_file2,out_file)
      GS_Fusion_main(in_file1,in_file2,out_file)
      
     
      
      
      
      
      
