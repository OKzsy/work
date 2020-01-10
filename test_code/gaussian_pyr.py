# !/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2019/12/3 10:58
# @Author  : zhaoss
# @FileName: gaussian_pyr.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import sys
import glob
import gc
import math
import time
import fnmatch
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def resize(src_dst, dst_xsize, dst_ysize, seq):
    """
    根据输入的目标影像行列数对原始影像进行缩放，缩放方法为双线性插值
    :param src_dst: 原始数据集
    :param dst_xsize: 目标影像列数
    :param dst_ysize: 目标影像行数
    :return: 返回重采样后的目标影像数据集
    """
    # 根据目标大小，在内存创建结果影像
    tmp_dst_path = r'/vsimem/tmp_dst_{}.tiff'.format(str(seq))
    gdal.Translate(tmp_dst_path, src_dst, resampleAlg=gdalconst.GRA_Bilinear, format='GTiff', width=dst_xsize,
                   height=dst_ysize, outputType=gdalconst.GDT_Float32)
    tmp_dst = gdal.Open(tmp_dst_path)
    src_dst = None
    gdal.Unlink(tmp_dst_path)
    gc.collect()
    return tmp_dst


def Extend(xs, ys, matrix):
    """
    根据滤波模板的大小，对原始影像矩阵进行外扩。
    :param xs: 滤波模板的xsize，要求为奇数
    :param ys: 滤波模板的ysize，要求为奇数
    :param matrix: 原始影像矩阵
    :return: 依据模板大小扩展后的矩阵
    """
    xs_fill = int((xs - 1) / 2)
    ys_fill = int((ys - 1) / 2)
    # 使用镜像填充
    extended_val = np.pad(matrix, ((ys_fill, ys_fill), (xs_fill, xs_fill)), "reflect")
    matrix = None
    return extended_val


def gaussian_template_one(sigma_val):
    # opencv认为当图像为8bit时，其能量集中再3个方差内，否则为4个方差内，有待考究
    # ksize = round(2 * round(3 * sigma_val) + 1)
    ksize = round(2 * round(4 * sigma_val) + 1)
    template = np.zeros(ksize, dtype=np.float32)
    for element in range(ksize):
        u = element - ksize // 2
        template[element] = math.exp(-u ** 2 / (2 * sigma_val ** 2))
    return ksize, template / np.sum(template)


def img_filtering(xs, ys, ori_xsize, ori_ysize, kernel, ext_img):
    """

    :param xs: 卷积核大小：列
    :param ys: 卷积核大小：行
    :param kernel: 卷积核
    :param ext_img: 经扩展后的影像
    :return: 滤波后的影像
    """
    # 使用切片后影像的波段书
    # 创建切片后存储矩阵
    filtered_img_h = np.zeros((ori_ysize + ys - 1, ori_xsize), dtype=np.float32)
    for icol in range(xs):
        filtered_img_h += ext_img[:, icol: icol + ori_xsize] * kernel[icol]
    ext_img = None
    filtered_img = np.zeros((ori_ysize, ori_xsize), dtype=np.float32)
    for irow in range(ys):
        filtered_img += filtered_img_h[irow: irow + ori_ysize, :] * kernel[irow]
    filtered_img_h = None
    return filtered_img


def scale_space(sigma):
    """
    计算高斯尺度金子塔的相对模糊尺度
    :param sigma: 自定义高斯金字塔初始尺度
    :param camera_sigma: 影像采集时镜头的模糊尺度
    :return: 尺度金字塔的相对模糊模糊尺度
    """
    # 定义高斯尺度空间中每组各层的尺度间隔
    k = 2 ** (1 / 3)
    # 计算该层的尺度空间参数
    scales_para = []
    scales_para.append(sigma)
    for iscal_spatial in range(1, 6):
        sig_prev = k ** (iscal_spatial - 1) * sigma
        sig_total = sig_prev * k
        scales_para.append(math.sqrt(sig_total ** 2 - sig_prev ** 2))
    return scales_para[:]


def adjustLocalExtrema(dog, o, l, r, c):
    """
    确定局部极值
    :param dog: 高斯差分金字塔
    :param o: 组数信息
    :param l: 层数信息
    :param r: 疑似极值点行
    :param c: 疑似极值点列
    :return:
    """
    # img_scale = 1 / global_maximun
    img_scale = 1 / 255
    deriv_scale = img_scale * 0.5
    second_deriv_scale = img_scale
    cross_seriv_scale = img_scale * 0.25
    xr = xc = xl = contr = 0
    istep = 0
    while istep < sift_max_interp_steps:
        local_detect_img = dog[l - 1: l + 2, :, :]
        dx = (local_detect_img[1, r, c + 1] - local_detect_img[1, r, c - 1]) * deriv_scale
        dy = (local_detect_img[1, r + 1, c] - local_detect_img[1, r - 1, c]) * deriv_scale
        ds = (local_detect_img[2, r, c] - local_detect_img[0, r, c]) * deriv_scale
        dD = np.array([dx, dy, ds])
        v2 = local_detect_img[1, r, c] * 2
        dxx = (local_detect_img[1, r, c + 1] + local_detect_img[1, r, c - 1] - v2) * second_deriv_scale
        dyy = (local_detect_img[1, r + 1, c] + local_detect_img[1, r - 1, c] - v2) * second_deriv_scale
        dss = (local_detect_img[2, r, c] + local_detect_img[0, r, c] - v2) * second_deriv_scale
        dxy = (local_detect_img[1, r + 1, c + 1] - local_detect_img[1, r + 1, c - 1] - \
               local_detect_img[1, r - 1, c + 1] + local_detect_img[1, r - 1, c - 1]) * cross_seriv_scale
        dxs = (local_detect_img[2, r, c + 1] - local_detect_img[2, r, c - 1] - \
               local_detect_img[0, r, c + 1] + local_detect_img[0, r, c - 1]) * cross_seriv_scale
        dys = (local_detect_img[2, r + 1, c] - local_detect_img[2, r - 1, c] - \
               local_detect_img[0, r + 1, c] + local_detect_img[0, r - 1, c]) * cross_seriv_scale
        H = np.array([[dxx, dxy, dxs], [dxy, dyy, dys], [dxs, dys, dss]])
        X = np.dot(np.linalg.inv(H), dD)
        xc, xr, xl = -X
        if abs(xc) < 0.5 and abs(xr) < 0.5 and abs(xl) < 0.5:
            break
        int_max = 32767 / 3
        if abs(xc) > int_max or abs(xr) > int_max or abs(xl) > int_max:
            return False, r, c, l
        c += int(round(xc))
        r += int(round(xr))
        l += int(round(xl))
        if l < 1 or l > 3 or r < sift_img_border or r > local_detect_img.shape[1] - sift_img_border \
                or c < sift_img_border or c > local_detect_img.shape[2] - sift_img_border:
            return False, r, c, l
        istep += 1
    if istep >= sift_max_interp_steps:
        return False, r, c, l
    local_detect_img = dog[l - 1: l + 2, :, :]
    dx = (local_detect_img[1, r, c + 1] - local_detect_img[1, r, c - 1]) * deriv_scale
    dy = (local_detect_img[1, r + 1, c] - local_detect_img[1, r - 1, c]) * deriv_scale
    ds = (local_detect_img[2, r, c] - local_detect_img[0, r, c]) * deriv_scale
    dD = np.array([dx, dy, ds])
    t = np.dot(dD, -X)

    contr = local_detect_img[1, r, c] * img_scale + t * 0.5
    if abs(contr) * 3 < contrastThreshold:
        return False, r, c, l
    v2 = local_detect_img[1, r, c] * 2
    dxx = (local_detect_img[1, r, c + 1] + local_detect_img[1, r, c - 1] - v2) * second_deriv_scale
    dyy = (local_detect_img[1, r + 1, c] + local_detect_img[1, r - 1, c] - v2) * second_deriv_scale
    dxy = (local_detect_img[1, r + 1, c + 1] - local_detect_img[1, r + 1, c - 1] - \
           local_detect_img[1, r - 1, c + 1] + local_detect_img[1, r - 1, c - 1]) * cross_seriv_scale
    tr = dxx + dyy
    det = dxx * dyy - dxy * dxy
    if (det <= 0) or (tr * tr * edgeThreshold >= (edgeThreshold + 1) * (edgeThreshold + 1) * det):
        return False, r, c, l
    kpt_y = (r + xr) * (1 << o)
    kpt_x = (c + xc) * (1 << o)
    kpt_octave = o + (l << 8) + (int(round((xl + 0.5) * 255)) << 16)
    kpt_size = init_sigma * math.pow(2.0, (l + xl) / 3) * (1 << o) * 2
    kpt_response = abs(contr)
    local_tmp_point = [kpt_y, kpt_x, kpt_octave, kpt_size, kpt_response]
    return local_tmp_point, r, c, l


def calcOrientationHist(guass_matrix, ext_point, radius, local_sigma, n):
    """
    在特征点局部区域计算特征点的主方向
    :param guass_matrix: 离特征点所在尺度层最近的高斯模糊层
    :param ext_point: 特征点所在坐标（行，列）
    :param radius: 计算幅值和特征点主方向区域的半径
    :param local_sigma:特征点所在层计算高斯函数的方差
    :param n:用于直方图统计的区间个数（0-360度，分36个区间）
    :return:特征点的主方向和幅值（有可能有多个）
    """
    anchor_x = ext_point[0]
    anchor_y = ext_point[1]
    rows = guass_matrix.shape[0]
    cols = guass_matrix.shape[1]
    star_x = -radius if (anchor_x - radius) > 0 else (1 - anchor_x)
    star_y = -radius if (anchor_y - radius) > 0 else (1 - anchor_y)
    end_x = radius if (rows - anchor_x - radius) > 1 else (rows - anchor_x - 2)
    end_y = radius if (cols - anchor_y - radius) > 1 else (cols - anchor_y - 2)
    # 生成所在区域窗口位置索引，用于计算高斯权重
    x = list(range(star_x, end_x + 1))
    y = list(range(star_y, end_y + 1))
    weight_index = np.meshgrid(y, x)
    expf_scale = -1 / (2 * local_sigma * local_sigma)
    weight = np.exp((weight_index[1] * weight_index[1] + weight_index[0] * weight_index[0]) * expf_scale)
    weight_index = None
    # 计算梯度
    xx = list(range(star_x - 1 + anchor_x, end_x + 2 + anchor_x))
    yy = list(range(star_y - 1 + anchor_y, end_y + 2 + anchor_y))
    grad_index = np.meshgrid(yy, xx)
    # 获取计算梯度区域数据
    grad_matrix = guass_matrix[grad_index[1], grad_index[0]]
    grad_index = None
    # 计算列方向梯度
    grad_x = grad_matrix[1: -1, 2:] - grad_matrix[1: -1, 0: -2]
    # 计算行方向梯度（和公式符号相反，为了和opencv保持一致）
    grad_y = grad_matrix[0: -2, 1: -1] - grad_matrix[2:, 1: -1]
    grad_matrix = None
    # 计算角度
    ori = ((np.arctan2(grad_y, grad_x) + 2 * np.pi) % (2 * np.pi)) * (180 / np.pi)
    # 计算幅值
    mag = np.sqrt(grad_x * grad_x + grad_y * grad_y)
    # 计算经高斯加权后的累计幅值
    bin_index = np.round((n / 360) * ori).astype(np.int)
    bin_index = np.where(bin_index >= n, bin_index - n, bin_index)
    bin_index = np.where(bin_index < 0, bin_index + n, bin_index)
    ori = None
    # 对幅值进行加权
    weight_mag = mag * weight
    mag = None
    # 统计幅值直方图
    temphist = np.zeros(n + 4, dtype=np.float32)
    for ibin in range(0, n):
        tmp_index = np.where(bin_index == ibin)
        tmp_sum = np.sum(weight_mag[tmp_index])
        temphist[ibin + 2] = tmp_sum
    # smooth the histogram
    temphist[0] = temphist[n]
    temphist[1] = temphist[n + 1]
    temphist[-2] = temphist[2]
    temphist[-1] = temphist[3]
    hist = np.zeros(n, dtype=np.float32)
    for ihist in range(2, n + 2):
        hist[ihist - 2] = (temphist[ihist - 2] + temphist[ihist + 2]) * (1 / 16) + \
                          (temphist[ihist - 1] + temphist[ihist + 1]) * (4 / 16) + \
                          temphist[ihist] * (6 / 16)
    temphist = None
    gc.collect()
    return hist.max(), hist[:]


def detect_ext_points(gauss_pyr, gauss_dog_pyr, octave, points):
    """

    :param gauss_pyr: 高斯金字塔
    :param gauss_dog_pyr: 高斯差分金子塔
    :param octave: 所在层数信息
    :return: 精确极值点位置和所在尺度空间信息
    """
    points = set()
    # 计算用于初步过滤极值点的阈值
    threshold = math.floor(0.5 * contrastThreshold / 3 * global_maximun)
    n = SIFT_ORI_HIST_BINS
    # 获取差分金字塔影像的行列数
    channels, rows, cols = gauss_dog_pyr.shape
    # 循环差分金字塔中间三层寻找极值点
    for ilayer in range(1, 4):
        # 获取包含ilayer，ilayer - 1，ilayer + 1 共三层的影像用于检测
        detect_img = gauss_dog_pyr[ilayer - 1: ilayer + 2, :, :]
        for irow in range(sift_img_border, rows - sift_img_border):
            for icol in range(sift_img_border, cols - sift_img_border):
                # 判断中心点是否满足阈值要求，如果不满足直接跳过
                val = detect_img[1, irow, icol]
                if abs(val) < threshold:
                    continue
                # 获取待检测窗口
                detect_win = detect_img[:, irow - 1: irow + 2, icol - 1: icol + 2]
                if ((val > 0) and (val >= detect_win.max())) or ((val < 0) and (val <= detect_win.min())):
                    r, c, l = irow, icol, ilayer
                    tmp_point, r1, c1, l1 = adjustLocalExtrema(gauss_dog_pyr, octave, l, r, c)
                    if tmp_point is False:
                        continue
                    scl_octv = tmp_point[3] * 0.5 / (1 << octave)

                    # 计算特征点主方向
                    omax, hist = calcOrientationHist(gauss_pyr[l1], (r1, c1), int(round(SIFT_ORI_RADIUS * scl_octv)),
                                                     SIFT_ORI_SIG_FCTR * scl_octv, n)

                    mag_thr = omax * SIFT_ORI_PEAK_RATIO
                    for ihist in range(0, n):
                        pre_ihist = ihist - 1 if ihist > 0 else n - 1
                        next_ihist = ihist + 1 if ihist < n - 1 else 0
                        if hist[ihist] > hist[pre_ihist] and hist[ihist] > hist[next_ihist] and hist[ihist] >= mag_thr:
                            bin = ihist + 0.5 * (hist[pre_ihist] - hist[next_ihist]) / (
                                        hist[pre_ihist] - 2 * hist[ihist] + hist[next_ihist])
                            bin = n + bin if bin < 0 else bin
                            bin = bin - n if bin >= n else bin
                            angle = 360 - ((360 / n) * bin)
                            flt_epslon = 1.192092896e-07
                            if abs(angle - 360.0) < flt_epslon:
                                angle = 0.0
                            local_tmp_point = tmp_point[:]
                            local_tmp_point.append(angle)
                            points.append(local_tmp_point)
                            local_tmp_point = None
                            pass
                    pass
            pass
        pass
    pass

    return 1


def build_dog(src_array, scale_para):
    """
    根据空间尺度参数构建高斯差分金字塔
    :param src_array: 构建高斯差分金字塔的初始数据
    :param scale_para: 高斯空间尺度参数
    :return: 高斯差分金字塔和高斯金字塔下一层初始数据
    """
    xsize = src_array.shape[1]
    ysize = src_array.shape[0]
    # 创建存储高斯差分金字塔的数组
    gauss_matrix = np.zeros((6, ysize, xsize), dtype=np.float32)
    dog_matrix = np.zeros((5, ysize, xsize), dtype=np.float32)
    for ilayer in range(6):
        if ilayer == 0:
            gauss_matrix[ilayer, :, :] = src_array
            continue
        sigmaf = scale_para[ilayer]
        win_size, template = gaussian_template_one(sigmaf)
        kernel_xsize = kernel_ysize = win_size
        # 结合滤波函数对待滤波影像进行边缘扩展，目的是保证滤波结果和原始影像大小一致
        extended_img = Extend(kernel_xsize, kernel_ysize, src_array)
        # 使用模板进行滤波
        filtered_img = img_filtering(kernel_xsize, kernel_ysize, xsize, ysize, template, extended_img)
        extended_img = None
        src_array = filtered_img
        filtered_img = None
        gauss_matrix[ilayer, :, :] = src_array
        # 输出下高斯金字塔下一层的原始数据
        if ilayer == 3:
            mem_driver = gdal.GetDriverByName("MEM")
            next_dst = mem_driver.Create('', xsize, ysize, 1, gdal.GDT_Float32)
            next_dst.GetRasterBand(1).WriteArray(src_array)
        # 计算高斯差分金字塔并存储
        dog_matrix[ilayer - 1, :, :] = gauss_matrix[ilayer, :, :] - gauss_matrix[ilayer - 1, :, :]
        gc.collect()
    return next_dst, dog_matrix, gauss_matrix


def pyramid(octave_val, src_dst, points, scale, n=0):
    if n == octave_val:  # 当达到指定层数后，返回监测的极值点
        # 返回极值点，可是设定在该返回位置做最后一层
        # 获取原始数据集的基本信息
        src_xsize = src_dst.RasterXSize
        src_ysize = src_dst.RasterYSize
        new_dst = resize(src_dst, int(src_xsize / 2), int(src_ysize / 2), n)  # 缩小一倍
        src_dst = None
        filtered_img = new_dst.ReadAsArray()
        # 建立高斯差分金字塔
        next_dst, dog_pyr, gauss_pyr = build_dog(filtered_img, scale)
        filtered_img = None
        # 检测极值点
        ext_points = detect_ext_points(gauss_pyr, dog_pyr, n)
        return ext_points
    else:
        if n == 0:
            # 获取原始数据集的基本信息
            src_xsize = src_dst.RasterXSize
            src_ysize = src_dst.RasterYSize
            new_dst = resize(src_dst, src_xsize * 2, src_ysize * 2, n)  # 放大一倍
            src_dst = None
            src_val = new_dst.ReadAsArray()
            # 针对第一组第一层需要考虑镜头模糊度进行特殊处理
            init_sigma_diff = math.sqrt(scale[0] ** 2 - (2 * init_camera_sigma) ** 2)
            win_size, template = gaussian_template_one(init_sigma_diff)
            kernel_xsize = kernel_ysize = win_size
            # 结合滤波函数对待滤波影像进行边缘扩展，目的是保证滤波结果和原始影像大小一致
            extended_img = Extend(kernel_xsize, kernel_ysize, src_val)
            # 使用模板进行滤波
            filtered_img = img_filtering(kernel_xsize, kernel_ysize, src_xsize * 2, src_ysize * 2, template,
                                         extended_img)
            extended_img = None
            # 建立高斯差分金字塔
            next_dst, dog_pyr, gauss_pyr = build_dog(filtered_img, scale)
            filtered_img = None
            # 检测极值点
            ext_points = detect_ext_points(gauss_pyr, dog_pyr, n, points[:])
            return pyramid(octave_val, next_dst, ext_points[:], scale, n + 1)
        else:
            # 获取原始数据集的基本信息
            src_xsize = src_dst.RasterXSize
            src_ysize = src_dst.RasterYSize
            new_dst = resize(src_dst, int(src_xsize / 2), int(src_ysize / 2), n)  # 缩小一倍
            src_dst = None
            filtered_img = new_dst.ReadAsArray()
            # 建立高斯差分金字塔
            next_dst, dog_pyr, gauss_pyr = build_dog(filtered_img, scale)
            filtered_img = None
            # 检测极值点
            ext_points = detect_ext_points(gauss_pyr, dog_pyr, n)
            return pyramid(octave_val, next_dst, ext_points[:], scale, n + 1)


def main(in_fn, band_index):
    global init_sigma
    init_sigma = 1.6
    global init_camera_sigma
    init_camera_sigma = 0.5
    global global_maximun
    global contrastThreshold
    contrastThreshold = 0.04
    global sift_img_border
    sift_img_border = 5
    global sift_max_interp_steps
    sift_max_interp_steps = 5
    global edgeThreshold
    edgeThreshold = 10.0
    global SIFT_ORI_HIST_BINS
    SIFT_ORI_HIST_BINS = 36
    global SIFT_ORI_SIG_FCTR
    SIFT_ORI_SIG_FCTR = 1.5
    global SIFT_ORI_RADIUS
    SIFT_ORI_RADIUS = 3 * SIFT_ORI_SIG_FCTR
    global SIFT_ORI_PEAK_RATIO
    SIFT_ORI_PEAK_RATIO = 0.8
    # 读取影像
    src_dst = gdal.Open(in_fn)
    xsize = src_dst.RasterXSize
    ysize = src_dst.RasterYSize
    ori_band = src_dst.GetRasterBand(band_index)
    # 提取单波段为一个数据集进行高斯尺度金字塔构建
    driver = gdal.GetDriverByName('MEM')
    src_one_dst = driver.Create('', xsize, ysize, 1, gdal.GDT_Float32)
    src_one_dst.GetRasterBand(1).WriteArray(ori_band.ReadAsArray())
    global_maximun = ori_band.ComputeRasterMinMax(True)[1]
    src_dst = ori_band = None
    # 确定高斯金子塔的组数
    octave = math.floor(math.log(min(xsize, ysize), 2) / 2)
    if octave > 5:
        octave = 5
    # 计算该层的高斯尺度空间
    scale = scale_space(init_sigma)
    # 构建高斯金字塔并检测极值点
    extreme_points = []
    extreme_points = pyramid(octave, src_one_dst, extreme_points[:], scale)
    return None


if __name__ == '__main__':
    # 支持中文路径
    gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
    # 支持中文属性字段
    gdal.SetConfigOption("SHAPE_ENCODING", "GBK")
    # 注册所有ogr驱动
    ogr.RegisterAll()
    # 注册所有gdal驱动
    gdal.AllRegister()
    start_time = time.time()
    in_file = r"F:\SIFT\left_one_band.PNG"
    # in_file = r"F:\test_data\new_test\GF2_20180718_L1A0003330812_sha.tiff"
    band_idx = 1
    main(in_file, band_idx)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
