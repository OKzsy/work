import sys
try:
    from osgeo import gdal
except ImportError:
    import gdal
import cv2 as cv
import numpy as np
# tif读入和写出
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

def writeTiff(im_data,im_width,im_height,im_bands,im_geotrans,im_proj,path):
    if 'uint8' in im_data.dtype.name:
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
        im_bands, (im_height, im_width) = 1,im_data.shape
        #创建文件
    driver = gdal.GetDriverByName("GTIFF")
    dataset = driver.Create(path, im_width, im_height, im_bands, datatype)
    if(dataset!= None):
        dataset.SetGeoTransform(im_geotrans) #写入仿射变换参数
        dataset.SetProjection(im_proj) #写入投影
    for i in range(im_bands):
        dataset.GetRasterBand(i+1).WriteArray(im_data[i])
    del dataset

in_file=r"C:\Users\01\Desktop\zm_roi_prob.tif"
out_file=r"C:\Users\01\Desktop\zm_roi_prob_bi.jpg"
data, in_band, geotransform, projection=Tif_read(in_file)
# index1=np.where(data>0.97)
# index2=np.where(data<=0.97)
# data[index1]=255
# data[index2]=0
data=(data*255)
data=np.uint8(data)
xsize,ysize=data.shape
#writeTiff(data,ysize,xsize,1,geotransform, projection,out_file)
cv.imwrite(out_file,data)