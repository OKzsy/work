import numpy as np

def nwhere(data, value):
    # 样本总个数
    total_sample = data.shape[0]
    ge_index = np.zeros(total_sample, dtype=np.uint32)
    lt_index = np.zeros(total_sample, dtype=np.uint32)
    ge_count = 0
    lt_count = 0
    for i in range(total_sample):
        if min(data[i], value) == value:
            ge_index[ge_count] = i
            ge_count += 1
        else:
            lt_index[lt_count] = i
            lt_count += 1
    return ge_index[0:ge_count], ge_count, lt_index[0:lt_count], lt_count
