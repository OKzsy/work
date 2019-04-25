import numpy as np

test_list = [1, 2.2, 2.5, 2.7, 3.1, 3.5, 3.8, 3.9, 4.1, 4.9]
test_arr = np.array(test_list)
max = np.max(test_arr)
min = np.min(test_arr)
r = max - min

bins = np.arange(start=int(test_arr.min()), stop=int(test_arr.max())+2, step=1)
n, bin = np.histogram(test_arr, bins=bins, density=True)
print('end')
