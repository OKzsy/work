#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2020/8/3 16:25
# @Author  : zhaoss
# @FileName: test.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import time

# 定义常量
x1, x2, y1, y2 = -1.8, 1.8, -1.8, 1.8
c_real, c_imag = -0.62772, -0.42193


# def print_time(func):
#     def my_func(*args, **kwargs):
#         start_time = time.time()
#         result = func(*args, **kwargs)
#         end_time = time.time()
#         print(func.__name__ + " took: %.4f secs." % (end_time - start_time))
#         return result
#
#     return my_func


def calculate_z_serial_purepython(maxiter, zs, cs):
    output = [0] * len(zs)
    for i in range(len(zs)):
        n = 0
        z = zs[i]
        c = cs[i]
        while abs(z) < 2 and n < maxiter:
            z = z * z + c
            n += 1
        output[i] = n
    return output


def calc_prue_python(desired_width, max_iterations):
    x_step = (float(x2 - x1) / float(desired_width))
    y_step = (float(y1 - y2) / float(desired_width))
    x = []
    y = []
    ycoord = y2
    while ycoord > y1:
        y.append(ycoord)
        ycoord += y_step
    xcoord = x1
    while xcoord < x2:
        x.append(xcoord)
        xcoord += x_step
    zs = []
    cs = []
    for ycoord in y:
        for xcoord in x:
            zs.append(complex(xcoord, ycoord))
            cs.append(complex(c_real, c_imag))
    print('Length of x:', len(x))
    print('Total elements:', len(zs))
    output = calculate_z_serial_purepython(max_iterations, zs, cs)
    assert sum(output) == 33219980
    return None


def main():
    calc_prue_python(desired_width=1000, max_iterations=300)
    return None


if __name__ == '__main__':
    main()
