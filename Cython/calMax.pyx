cimport numpy as np
import cython

@cython.wraparound(False)
@cython.boundscheck(False)
def unique_cython_int(np.ndarray[np.int64_t] a):
    cdef int i, max_i
    cdef int n = len(a)
    max_i = a[0]
    for i in range(n):
        if a[i] <= max_i:
            continue
        else:
            max_i = a[i]
    return max_i