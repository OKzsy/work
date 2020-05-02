import numpy as np

arr = np.arange(75).reshape(3, 5, 5)
print(arr)
res = arr.flatten(order='F')
bands = 3
for x in range(0, res.size, bands):
    print(res[x: x + bands].tolist())
print('end')
