import numpy as np
cimport numpy as np
import cython

def cal_gini_index(data):
    return cal_gini(data)


@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
cdef double cal_gini(np.int16_t [:] data):
    """
    计算给定数据集的gini指数
    :param data: numpy array 数据集
    :return: Gini指数
    """
    cdef double gini = 0
    cdef Py_ssize_t total_sample, i
    cdef int min_i, max_i, tmp
    cdef Py_ssize_t real_total, j
    # 样本总个数
    total_sample = data.shape[0]
    if total_sample == 0:
        return 0  
    max_i = data[0]
    min_i = data[0]
    for i in range(total_sample):
        max_i = max(max_i, data[i])
        min_i = min(min_i, data[i])
    min_i = min(min_i, 0)
    max_i -= min_i
    real_total = max_i + 1
    label_count = np.zeros(real_total, dtype=np.double)
    cdef np.double_t [:] label_count_view = label_count
    for i in range(total_sample):
        tmp = data[i] - min_i
        label_count_view[tmp] += 1
    for j in range(real_total):
        gini += (label_count_view[j] * label_count_view[j])
    gini = 1 - gini / <double>(total_sample * total_sample)
    return gini