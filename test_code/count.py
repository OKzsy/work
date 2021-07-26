#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2021/5/26 18:17
# @Author  : zhaoss
# @FileName: count.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

from cv2 import cv2

# 读取
img_rice = cv2.imread(r"E:\DIP3\DIP3E_Original_Images_CH09\Fig0940(a)(rice_image_with_intensity_gradient).tif")
# cv2.imshow('rice', img_rice)
# 灰度化
img_gray = cv2.cvtColor(img_rice, cv2.COLOR_BGR2GRAY)
# cv2.imshow('gray', img_rice)
# 二值化
ret, thresh1 = cv2.threshold(img_gray, 123, 255, cv2.THRESH_BINARY)
# cv2.imshow('thresh', thresh1)

# 腐蚀和膨胀
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))  # 定义矩形结构元素

img_erode = cv2.erode(thresh1, kernel, iterations=3)
# cv2.imshow('erode', img_erode)

img_dilated = cv2.dilate(img_erode, kernel)
# 边缘检测
contours, hierarchy = cv2.findContours(img_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

count = 0
ave_area = 0
for i in range(len(contours)):
    area = cv2.contourArea(contours[i])
    if area > 20:

        count = count + 1
        ave_area = ave_area + area
        rect = cv2.boundingRect(contours[i])  # 提取矩形坐标

        print("number:{} x:{} y:{} area:{}".format(count, rect[0], rect[1], area))  # 打印坐标

        cv2.rectangle(img_rice, rect, (0, 255, 0), 1)  # 绘制矩形
        if area > 150:
            count = count + 1
            cv2.putText(img_rice, str({count, count - 1}), (rect[0], rect[1]), cv2.FONT_HERSHEY_COMPLEX, 0.4,
                        (0, 255, 0), 1)  # 在米粒左上角写上编号
        else:

            cv2.putText(img_rice, str(count), (rect[0], rect[1]), cv2.FONT_HERSHEY_COMPLEX, 0.4, (0, 255, 0),
                        1)  # 在米粒左上角写上编号

ave_area = ave_area / count
# 输出
print('总个数是：{}，平均面积是：{}'.format(count, ave_area))
# cv2.imshow("Contours", img_rice)
#
# cv2.waitKey(0)
# cv2.destroyAllWindows()
