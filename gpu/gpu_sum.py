#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2022/1/18 10:06
# @Author  : zhaoss
# @FileName: gpu_sum.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""
import numba
from numba import cuda
import numpy as np
import math
from time import time


@cuda.jit
def vector_add(a, b, result, n):
    c = dict()
    print(numba.typeof(c))
    # idx = cuda.threadIdx.x + cuda.blockDim.x * cuda.blockIdx.x
    # if idx < n:
    #     result[idx] = a[idx] + b[idx]


def main():
    n = 20000000
    x = np.random.uniform(10, 20, n)
    y = np.random.uniform(10, 20, n)
    # x = np.arange(n).astype(np.int32)
    # y = 2 * x

    start = time()
    # 使用默认流
    # Host To Device
    x_device = cuda.to_device(x)
    y_device = cuda.to_device(y)
    z_device = cuda.device_array(n)
    z_streams_device = cuda.device_array(n)
    #
    threads_per_block = 1024
    blocks_per_grid = math.ceil(n / threads_per_block)

    # Kernel
    vector_add[blocks_per_grid, threads_per_block](x_device, y_device, z_device, n)

    # Device To Host
    default_stream_result = z_device.copy_to_host()
    cuda.synchronize()
    print("gpu vector add time " + str(time() - start))

    start = time()

    # 使用5个流
    number_of_streams = 2
    # 每个流处理的数据量为原来的 1/5
    segment_size = math.ceil(n / number_of_streams)

    # 创建5个cuda stream
    stream_list = list()
    for i in range(0, number_of_streams):
        stream = cuda.stream()
        stream_list.append(stream)

    threads_per_block = 1024
    # 每个stream的处理的数据变为原来的1/5
    blocks_per_grid = math.ceil(segment_size / threads_per_block)
    streams_result = np.empty(n)

    # 启动多个stream
    for i in range(0, number_of_streams):
        # 传入不同的参数，让函数在不同的流执行
        start_point = i * segment_size
        end_point = (i + 1) * segment_size
        if end_point > n:
            end_point = n

        # Host To Device
        x_i_device = cuda.to_device(x[start_point: end_point], stream=stream_list[i])
        y_i_device = cuda.to_device(y[start_point: end_point], stream=stream_list[i])

        # Kernel
        vector_add[blocks_per_grid, threads_per_block, stream_list[i]](
            x_i_device,
            y_i_device,
            z_streams_device[start_point: end_point],
            segment_size)

        # Device To Host
        streams_result[start_point: end_point] = \
            z_streams_device[start_point: end_point].copy_to_host(stream=stream_list[i])

    cuda.synchronize()

    print("gpu streams vector add time " + str(time() - start))
    if np.array_equal(default_stream_result, streams_result):
        print("result correct")


if __name__ == "__main__":
    main()


