import numpy as np
from numba import njit
import time
import cgini

@njit()
def cal_gini(data):
    """
    计算给定数据集的gini指数
    :param data: numpy array 数据集
    :return: Gini指数
    """
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
    label_count = np.zeros(real_total)
    for i in range(total_sample):
        tmp = data[i] - min_i
        label_count[tmp] += 1
    gini = 0
    for j in range(real_total):
        gini += (label_count[j] * label_count[j])
    gini = 1 - gini / (total_sample * total_sample)
    return gini


lable = np.random.randint(0, 50, 1000000, dtype=np.int16)
for _ in range(10):
    start_time = time.time()
    print(cgini.cal_gini_index(lable))
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
print('___________________________')
for _ in range(10):
    start_time = time.time()
    print(cal_gini(lable))
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))

