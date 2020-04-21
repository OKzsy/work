import sys

try:
    from osgeo import gdal
except ImportError:
    import gdal
import cv2 as cv
import numpy as np
from sklearn.preprocessing import MinMaxScaler


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
    nodata = in_band.GetNoDataValue()
    print(nodata)
    data = source_dataset.ReadAsArray(0, 0, xsize, ysize)
    source_dataset = None
    return data, in_band, geotransform, projection


def writeTiff(im_data, im_width, im_height, im_bands, im_geotrans, im_proj, path):
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
        im_bands, (im_height, im_width) = 1, im_data.shape
        # 创建文件
    driver = gdal.GetDriverByName("GTIFF")
    dataset = driver.Create(path, im_width, im_height, im_bands, datatype)
    if (dataset != None):
        dataset.SetGeoTransform(im_geotrans)  # 写入仿射变换参数
        dataset.SetProjection(im_proj)  # 写入投影
    for i in range(im_bands):
        dataset.GetRasterBand(i + 1).WriteArray(im_data[i])
    del dataset


def hist_calc(img, ratio):
    max = np.max(img)
    min = np.min(img)
    r = max - min

    bins = np.arange(r) + min
    # 调用Numpy实现灰度统计
    hist, bins = np.histogram(img, bins)
    total_pixels = img.shape[0] * img.shape[1]
    zero_pixels = np.where(img == 0)[0].shape[0]
    total_pixels = total_pixels - zero_pixels
    # 计算获得ratio%所对应的位置，
    # 这里ratio为0.02即为2%线性化，0.05即为5%线性化
    min_index = int(ratio * total_pixels)
    max_index = int((1 - ratio) * total_pixels)
    min_gray = 0
    max_gray = 0
    # 统计最小灰度值(A)
    sum = 0
    for i in range(hist.__len__()):
        if i != 0:
            sum = sum + hist[i]
            if sum > min_index:
                min_gray = i
                break
    # 统计最大灰度值(B)
    sum = 0
    for i in range(hist.__len__()):
        if i != 0:
            sum = sum + hist[i]
            if sum > max_index:
                max_gray = i
                break
    return min_gray, max_gray


def linearStretch(img, new_min, new_max, ratio):
    # 获取原图除去2%像素后的最小、最大灰度值(A、B)
    old_min, old_max = hist_calc(img, ratio)
    # 对原图中所有小于或大于A、B的像素都赋为A、B
    img1 = np.where(img < old_min, old_min, img)
    img2 = np.where(img1 > old_max, old_max, img1)
    print('old min = %d,old max = %d' % (old_min, old_max))
    print('new min = %d,new max = %d' % (new_min, new_max))

    # 按照线性拉伸公式计算新的灰度值
    img3 = np.uint8((new_max - new_min) / (old_max - old_min) * (img2 - old_min) + new_min)
    return img3


in_file = r"\\192.168.0.234\nydsj\user\DYR\变化检测\惠济区\2017测试区域选取\植被\区域5农作物与林地\GF2_20180416\区域tif\GF2312679220180416F_nongzuowu_test1.tif"
out_file = r"\\192.168.0.234\nydsj\user\DYR\变化检测\惠济区\2017测试区域选取\植被\区域5农作物与林地\GF2_20180416\区域tif\GF2312679220180416F_nongzuowu_test1_%2stretch.tif"
data, in_band, geotransform, projection = Tif_read(in_file)
c, x, y = data.shape
data_r = np.zeros_like(data)
for i in range(c):
    img = data[i]
    res = linearStretch(img, 0, 255, 0.02)
    data_r[i] = res

writeTiff(data_r, x, y, c, geotransform, projection, out_file)
