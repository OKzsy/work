import numpy as np

arr = np.arange(25).reshape(5, 5)
# print(arr)
# res = arr.flatten(order='F')
# bands = 3
# for x in range(0, res.size, bands):
#     print(res[x: x + bands].tolist())
# print('end')
txtpath = r"F:\test_data\test.csv"
np.savetxt(txtpath, arr, fmt='%.3f', delimiter=',')
