import numpy as np
cimport numpy as np
import cython

def cwhere(data, value):
    return where(data, value)


@cython.boundscheck(False)
@cython.wraparound(False)
cdef where(np.int16_t [:] data, np.int16_t value):
    """
    计算给定数据集的gini指数
    :param data: numpy array 数据集
    :return: Gini指数
    """

    cdef Py_ssize_t total_sample, i
    # 样本总个数
    total_sample = data.shape[0]
    if total_sample == 0:
        return 0  
    ge_index = np.zeros(total_sample, dtype=np.uint32)
    cdef np.uint32_t [:] ge_index_view = ge_index
    lt_index = np.zeros(total_sample, dtype=np.uint32)
    cdef np.uint32_t [:] lt_index_view = lt_index
    cdef Py_ssize_t ge_count, lt_count
    ge_count = 0
    lt_count = 0
    for i in range(total_sample):
        if min(data[i], value) == value:
            ge_index_view[ge_count] = i
            ge_count += 1
        else:
            lt_index_view[lt_count] = i
            lt_count += 1
            
    return ge_index[0:ge_count], ge_count, lt_index[0:lt_count], lt_count