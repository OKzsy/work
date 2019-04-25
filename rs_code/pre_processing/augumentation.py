import numpy as np
try:
    from osgeo import gdal
except ImportError:
    import gdal
import sys
import cv2 as cv


######以下几个函数是图像扩增的一些方法
def rot90(data, kwargs):  # 旋转90度
    return np.rot90(data, 1, axes=(0,1))


def rot180(data, kwargs):  # 旋转180度
    return np.rot90(data, 2, axes=(0,1))


def rot270(data, kwargs):  # 旋转270度
    return np.rot90(data, 3, axes=(0,1))


def flip_h(data, kwargs):  # 水平翻转
    return np.flip(data, axis=0)


def flip_v(data, kwargs):  # 垂直翻转
    return np.flip(data, axis=1)


def random_crop(data, kwargs):  # 随机裁剪，trans_size远小于图像的长宽
    trans_size = kwargs.get("trans_size")
    x,y,c=data.shape
    x_offset = np.random.randint(0, trans_size, 1)[0]
    y_offset = np.random.randint(0, trans_size, 1)[0]
    crop_data=np.zeros_like(data)
    crop_data[:(x-x_offset),:(y-y_offset)]=data[x_offset:,y_offset:]
    return crop_data


def rotate(data, kwargs):  # 任意角度旋转
    angle = kwargs.get("angle")
    center = kwargs.get("center", None)
    scale = kwargs.get("scale", 1.0)
    # 获取图像尺寸
    (h, w) = data.shape[0:2]

    # 若未指定旋转中心，则将图像中心设为旋转中心
    if center is None:
        center = (w / 2, h / 2)
    # 执行旋转
    M = cv.getRotationMatrix2D(center, angle, scale)
    return cv.warpAffine(data, M, (w, h))  # 返回旋转后的图像


def img_rescale(data, kwargs):  # rescale 按比例缩放
    weight = kwargs.get("weight")
    height = kwargs.get("height")
    return cv.resize(data,(0, 0), fx=weight, fy=height)


def img_resize(data, kwargs):  # 调整
    weight = kwargs.get("weight")
    height = kwargs.get("height")
    return cv.resize(data,(weight, height))


aug_func = [rot90, rot180, rot270, flip_h, flip_v, random_crop,
            rotate, img_rescale, img_resize]
aug_func_dict = {f.__name__: f for f in aug_func}


class Augumentation(object):

    def __init__(self, in_file, out_file):
        source_dataset = gdal.Open(in_file)
        if source_dataset is None:
            sys.exit('Problem opening file %s !' % in_file)

        xsize = source_dataset.RasterXSize
        ysize = source_dataset.RasterYSize
        self.geotransform = source_dataset.GetGeoTransform()
        self.projection = source_dataset.GetProjectionRef()
        self.in_band = source_dataset.GetRasterBand(1)
        self.data = source_dataset.ReadAsArray(0, 0, xsize, ysize)
        self.out_file = out_file

    def augument(self, aug_op, kwargs={}):
        data = self.data.transpose(1, 2, 0)
        data1 = aug_func_dict[aug_op](data, kwargs)
        data_result = data1.transpose(2, 0, 1)
        self._write_tiff(data_result)

    def _write_tiff(self, im_data):
        im_width = im_data.shape[2]
        im_height = im_data.shape[1]
        im_bands = im_data.shape[0]
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
            im_bands,(im_height, im_width) = 1,im_data.shape
            #创建文件
        driver = gdal.GetDriverByName("GTIFF")
        dataset = driver.Create(self.out_file, im_width, im_height, im_bands, datatype)
        if(dataset!= None):
            dataset.SetGeoTransform(self.geotransform) #写入仿射变换参数
            dataset.SetProjection(self.projection) #写入投影
        for i in range(im_bands):
            dataset.GetRasterBand(i + 1).SetNoDataValue(0)
            dataset.GetRasterBand(i+1).WriteArray(im_data[i, :, :])
        del dataset


def main(in_file, out_file, aug_op, kwargs):
    aug = Augumentation(in_file, out_file)
    aug.augument(aug_op, kwargs=kwargs)


if __name__ == '__main__':
    in_file=r"C:\docs\深度学习工程化\数据扩增\样例数据\GF2226639820170327F_shuiti.tif"
    out_file=r"C:\docs\GF2226639820170327F_shuiti_resize255.tif"
    main(in_file, out_file, 'img_resize', {'weight': 255, 'height': 255})



