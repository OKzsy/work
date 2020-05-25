import multiprocessing
import time
import numpy as np


def init_pool(arr_shared, shape, dt):
    global global_arr_shared
    global SHAPE
    global dtype
    global_arr_shared = arr_shared
    SHAPE = shape
    dtype = dt


def worker(i):
    start_time = time.time()
    new_arr = np.frombuffer(global_arr_shared, dtype).reshape(SHAPE)
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
    time.sleep(1)  # some other operations
    return new_arr[i, 0, 0]


if __name__ == '__main__':
    imgtype2ctype = {1: ['b', 'byte'], 2: ['H', 'uint16'], 3: ['h', 'int16'], 4: ['L', 'uint32'], 5: ['l', 'int32'],
                     6: ['f', 'float32'], 7: ['d', 'float64']}
    typecode = 1
    dt = np.dtype(imgtype2ctype[typecode][1])
    SHAPE = (3, 10, 10)
    arr = np.random.randint(low=1000, size=SHAPE).astype(dt)
    print(arr)
    arr_shared = multiprocessing.RawArray(imgtype2ctype[typecode][0], arr.ravel())
    # arr_shared = multiprocessing.RawArray('q', arr.ravel())
    arr = None
    with multiprocessing.Pool(processes=3, initializer=init_pool,
                              initargs=(arr_shared, SHAPE, dt)) as pool:  # initargs传入tuple
        for result in pool.map(worker, [0, 1, 2]):
            print(result)
    arr_shared = None
