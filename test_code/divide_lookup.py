# -*- coding:utf-8 -*-


import numpy as np
from bubblesort import list_bubblesort


def lookup(record, value):
    low = 0
    high = len(record) - 1
    count = 1
    find_ok = False
    while low <= high:
        middle = int((low + high) / 2)
        if record[middle] == value:
            find_ok = True
            break
        elif record[middle] > value:
            high = middle - 1
        else:
            low = middle + 1
        count += 1
    if find_ok:
        return count, middle
    else:
        return None


def main():
    disordered_record = list(np.random.randint(-10, 10, 20))
    sorted_record = list_bubblesort(disordered_record[:])
    find_value = 7
    res = lookup(sorted_record, find_value)
    print(sorted_record)
    if res:
        print(*res)
    else:
        print('没有找到')
    pass


if __name__ == '__main__':
    main()
