import numpy as np
cimport numpy as np
import cython

def funique(data):
    return cyunique(data)



@cython.wraparound(False)
@cython.boundscheck(False)
cdef cyunique(np.ndarray[np.int16_t] a):
    cdef int i, label_num, min_i, max_i, tmp
    cdef long int n = a.shape[0]
    label_num = 0
    max_i = np.max(a)
    min_i = np.min(a)
    min_i = min(min_i, 0)
    max_i -= min_i
    cdef np.ndarray[np.uint8_t, cast=True] unique = np.zeros(max_i + 1, dtype=bool)
    cdef np.ndarray[np.int16_t] label = np.zeros(max_i + 1, dtype=np.int16)
    cdef np.ndarray[np.uint32_t] label_count = np.zeros(max_i + 1, dtype=np.uint32)
    for i in range(n):
        tmp = a[i] - min_i
        label_count[tmp] += 1
        if not unique[tmp]:
            label_num += 1
            unique[tmp] = True
            label[tmp] = tmp
    cdef np.ndarray[np.int16_t] res_label = np.zeros(label_num, dtype=np.int16)
    cdef np.ndarray[np.uint32_t] res_label_count = np.zeros(label_num, dtype=np.uint32)
    cdef int ires = 0
    for i in range(max_i + 1):
        if unique[i]:
            res_label[ires] = label[i] + min_i
            res_label_count[ires] = label_count[i]
            ires += 1
    return (res_label, res_label_count)
