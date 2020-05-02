import csv
import datetime
import gc
import os
import sys
import shutil
import multiprocessing as mp
import time
import numpy as np
from tensorflow.keras.models import load_model
from retrying import retry

try:
    from osgeo import gdal
except ImportError:
    import gdal

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress

import warnings

warnings.filterwarnings("ignore", message="numpy.dtype size changed")

# 定义一些全局变量
SIZE_WIND = 7
NUM_XBLOCK = 100
TIF_FILE = r"/home/zhaoshaoshuai/test_data/model/tif_folder/GF6_20190820_L1A1119913673_sha.tif"
BASE_DIR = r"/home/zhaoshaoshuai/test_data/model"
MODEL_FILE = r"/home/zhaoshaoshuai/test_data/model/model/kbflow_model_lr0.0024356931030842383_hidden251.h5"
# # 当前目录
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 目录上一级
# FRONT_DIR = os.path.dirname(BASE_DIR)

FRONT_DIR = os.path.join(BASE_DIR, TIF_FILE.split(os.sep)[-1].split('.')[0])
if not os.path.exists(FRONT_DIR):
    os.makedirs(FRONT_DIR)
# 存储切割后影像的根目录
TEMP_TIF_DIR = os.path.join(FRONT_DIR, "temp_tifs")
# 存储分类结果的csv文件的根目录
CLASS_CSV_DIR = os.path.join(FRONT_DIR, "classification_csv_class")


# TIF_FILE = r"D:\test\tif\GF2_20190205_L1A0003823554_sha.tif"


class PathExistError(Exception):
    pass


def make_dir(path=None):
    """
    判断目录路径是否存在，不存在则生成，存在则中断程序并报错
    :return: 临时目录
    """
    if os.path.exists(path):
        raise PathExistError("{}该路径已存在，请确保路径唯一！".format(path))
    else:
        os.makedirs(path)


def main_raster(num_xblock=None, tif_file=None):
    """
    测量影像数据，返回要分割影像的数据
    :param num_xblock: 每块影像宽度
    :param tif_file: 传入的影像位置
    :param size_wind: 窗口大小，必须为奇数
    :return: 返回元组，元组第0位置为元组，包括：影像宽度，高度，波段数，数据类型；元组[1:]为分割影像的起始位置
    """
    # 用gdal打开图像
    source_dataset = gdal.Open(tif_file)
    if source_dataset is None:
        sys.exit('Problem opening file %s!' % tif_file)

    # 获取图像宽度，也为分割的总宽度
    xsize = source_dataset.RasterXSize
    # 获取图像高度
    ysize = source_dataset.RasterYSize
    # 获取图像波段数
    num_band = source_dataset.RasterCount
    # 获取影像的数据类型
    data_type = source_dataset.GetRasterBand(1).DataType

    tif_tuples = ((xsize, ysize, num_band, data_type),)
    num_xsize = 0
    for xoffset in range(0, xsize, num_xblock):
        if xoffset + num_xblock < xsize:
            temp = num_xsize
            num_xsize += num_xblock
            tif_tuples += (temp,)
        else:
            tif_tuples += (num_xsize,)

    source_dataset = None

    return tif_tuples


def block_raster(tif_file=None, base_property=None,
                 start_position=None, tif_dir_path=None):
    """
    切割影像
    :param tif_file: 传入的影像位置
    :param base_property: main_raster函数返回的第0位置的元组
    :param start_position: 切图的起始位置
    :param tif_dir_path: 生成小图的保存位置
    :param size_wind: 窗口大小
    :param num_xblock: 每块的列数
    :return: 返回切好后影像路径
    """
    # 四周窗口大小
    num_sub_size = int(SIZE_WIND / 2)
    # 影像宽度
    xsize = base_property[0]
    # 影像高度
    ysize = base_property[1]
    # 波段数
    num_band = base_property[2]
    # 影像数据类型
    data_type = base_property[3]

    # 创建输出影像
    file_name = "{}_{}_{}_{}.tif".format(start_position, 0, NUM_XBLOCK, ysize)
    reshape_file = os.path.join(tif_dir_path, file_name)
    out_driver = gdal.GetDriverByName('GTiff')
    if os.path.exists(reshape_file):
        out_driver.Delete(reshape_file)
    reshape_dataset = out_driver.Create(reshape_file, NUM_XBLOCK + 2 * num_sub_size, ysize + 2 * num_sub_size,
                                        num_band,
                                        data_type)  # 生成空的tif影像

    # 用gdal打开原始影像
    source_dataset = gdal.Open(tif_file)

    if source_dataset is None:
        sys.exit('Problem opening file %s!' % tif_file)

    for iband in range(num_band):
        in_band = source_dataset.GetRasterBand(1 + iband)
        out_band = reshape_dataset.GetRasterBand(1 + iband)
        # out_band.Fill(0)

        # 起点
        if start_position == 0:
            in_data = in_band.ReadAsArray(start_position, 0, NUM_XBLOCK + num_sub_size, ysize)
            out_band.WriteArray(in_data, num_sub_size, num_sub_size)
        # 终点
        elif start_position + NUM_XBLOCK > xsize:
            in_data = in_band.ReadAsArray(start_position - num_sub_size, 0, xsize - start_position, ysize)
            out_band.WriteArray(in_data, 0, num_sub_size)
        # 过程点
        else:
            in_data = in_band.ReadAsArray(start_position - num_sub_size, 0, NUM_XBLOCK + 2 * num_sub_size, ysize)
            out_band.WriteArray(in_data, 0, num_sub_size)

    # 关闭gdal相关对象
    source_dataset = None
    reshape_dataset = None
    in_data = None
    out_band = None
    in_band = None

    return reshape_file


def jit(reshape_file=None, start_position=None, base_property=None,
        max_len=None, class_dir_path=None):
    """
    中间计算
    :param reshape_file: 小图影像路径
    :param start_position: 切图的起始位置
    :param base_property: 原始影像相应属性数据元组
    :param class_dir_path: 分类后形成csv文件的保存目录
    :return:
    """
    out_file = os.path.join(class_dir_path, '{}_class.csv'
                            .format(os.path.splitext(os.path.basename(reshape_file))[0]))

    source_dataset = gdal.Open(reshape_file)

    if source_dataset is None:
        sys.exit('Problem opening file %s!' % reshape_file)

    tif_xsize = source_dataset.RasterXSize
    tif_ysize = source_dataset.RasterYSize

    block_data = source_dataset.ReadAsArray(0, 0, tif_xsize, tif_ysize)

    ysize = base_property[1]
    num_sub_size = int(SIZE_WIND / 2)
    final_lis = []
    for iyoffset in range(ysize):
        np_lis = np.empty((1, max_len))
        for ixoffset in range(NUM_XBLOCK):

            if block_data[:, (iyoffset + num_sub_size), (ixoffset + num_sub_size)].flatten()[0] > 0:
                isample_data = block_data[:, iyoffset:(iyoffset + SIZE_WIND),
                               ixoffset:(ixoffset + SIZE_WIND)].T.flatten()

                isample_data = np.concatenate((np.array([iyoffset + 0, ixoffset + start_position]), isample_data),
                                              axis=0).astype(np.uint16)
                np_lis = np.concatenate((np_lis, [isample_data])).astype(np.uint16)

        if len(np_lis) > 1:
            # 删除第一个空数据
            np_lis = np.delete(np_lis, 0, axis=0)
            # 将数组变成元组并放入np_tuple里面
            final_lis.append(np_lis)

    return final_lis, out_file


def run_model(final_lis=None, out_file=None):
    """
    模型分类
    :param final_lis: 跑模型所需数据
    :param out_file: 输出文件路径
    :return:
    """
    csv_data = []
    xind_list = []
    yind_list = []

    for icsv_lis in final_lis:
        for icsv_data in icsv_lis:
            csv_data.append([i for i in icsv_data[2:]])
            xind_list.append(icsv_data[0])
            yind_list.append(icsv_data[1])

    num_band = int(len(csv_data[0]) / (SIZE_WIND ** 2))
    csv_array = np.array(csv_data).reshape(len(csv_data), SIZE_WIND, SIZE_WIND, int(num_band))

    import tensorflow as tf

    gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.1)
    config = tf.ConfigProto(gpu_options=gpu_options)
    sess = tf.Session(config=config)

    model = load_model(MODEL_FILE)

    y_pred = model.predict_classes(csv_array / 10000.0, batch_size=512)

    try:
        out_csv = open(out_file, 'w', newline='')
        out_csv_writer = csv.writer(out_csv)
    except Exception:
        print("Write to out csv file failed, %s" % out_file)

    for iout in range(len(xind_list)):
        retry_write_to_csv(out_csv_writer, [xind_list[iout], yind_list[iout], y_pred[iout]])

    out_csv.close()
    y_pred = None
    csv_array = None
    out_csv_writer = None


@retry(stop_max_attempt_number=10, wait_fixed=1)
def retry_write_to_csv(csv_writer, csv_data):
    try:
        csv_writer.writerow(csv_data)
    except Exception:
        import traceback
        print("Failed to write to csv, Retrying...")
        traceback.print_exc()


def main_run(base_property=None, start_position=None, tif_dir_path=None,
             max_len=None, class_dir_path=None):
    """
    多进程的执行函数
    """
    start = time.time()
    gc.disable()
    reshape_file = block_raster(tif_file=TIF_FILE, base_property=base_property,
                                tif_dir_path=tif_dir_path, start_position=start_position)

    final_lis, out_file = jit(reshape_file=reshape_file, start_position=start_position,
                              base_property=base_property, max_len=max_len, class_dir_path=class_dir_path)

    if len(final_lis) > 0:
        run_model(final_lis=final_lis, out_file=out_file)

    gc.enable()
    gc.collect()
    end = time.time()
    file_name = os.path.join(BASE_DIR, "{}".format(os.getpid()))
    with open(file_name, "a") as f:
        name = out_file.split(os.sep)[-1]
        f.write("%s\ntotal_time: %.2f min.\n" % (name, (end - start) / 60))


def main():
    """
    计算开启进程数，执行run函数
    :return:
    """
    # 建立存储切割后影像的临时目录与保存分类后的csv文件目录
    now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    temp = TIF_FILE.split(os.sep)[-1].split(".")[0]
    tif_dir_name = "{}_{}".format(now, temp)
    tif_dir_path = os.path.join(TEMP_TIF_DIR, tif_dir_name)
    make_dir(tif_dir_path)

    model = MODEL_FILE.split(os.sep)[-1].split(".")[0]
    class_dir_name = "{}_{}".format(now, model)
    class_dir_path = os.path.join(CLASS_CSV_DIR, class_dir_name)
    make_dir(class_dir_path)

    tif_tuples = main_raster(tif_file=TIF_FILE, num_xblock=NUM_XBLOCK)
    max_len = SIZE_WIND * SIZE_WIND * tif_tuples[0][2] + 2
    # 开启多进程
    num_proc = 6
    print('Process:{}'.format(num_proc))
    #
    # 开启进程池
    pool = mp.Pool(processes=num_proc)

    # 判断开启进程数与处理影像列表的数量
    # 减掉元组第0位元素
    length = len(tif_tuples) - 1
    for i in range(length):
        # 进度条
        progress(i / length)

        pool.apply_async(main_run, args=(tif_tuples[0], tif_tuples[i + 1], tif_dir_path, max_len, class_dir_path))

    pool.close()
    pool.join()
    # length = len(tif_tuples) - 1
    # for i in range(length):
    #     # 进度条
    #     progress(i / length)
    #
    #     main_run(tif_tuples[0], tif_tuples[i + 1], tif_dir_path, max_len, class_dir_path)

    shutil.rmtree(tif_dir_path)
    shutil.rmtree(TEMP_TIF_DIR)
    # 进度条
    progress(1)


if __name__ == '__main__':
    start_time = time.time()
    #
    # if len(sys.argv[1:]) < 3:
    #     sys.exit('Problem reading input')
    # main(sys.argv[1], int(sys.argv[2]), sys.argv[3])
    main()
    end_time = time.time()
    file_name = os.path.join(BASE_DIR, "time.txt")
    with open(file_name, "w") as f:
        f.write("total_time: %.2f min." % ((end_time - start_time) / 60))
