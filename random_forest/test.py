import multiprocessing


def job(x, y):
    return x * y


if __name__ == "__main__":
    pool = multiprocessing.Pool(processes=2)
    res = []
    for i in range(3):
        a = i
        b = i + 10
        res.append(pool.apply_async(job, (a, b)))
    pool.close()
    pool.join()
    print([r.get() for r in res])
