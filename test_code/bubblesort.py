# -*- coding:utf-8 -*-
'''
利用冒泡排序算法进行排序
'''
import numpy as np
import random as rd


def list_bubblesort(record):
    # 用冒泡排序法对record进行排序
    i, compare = 0, 0
    record_len = len(record)
    while i < record_len:
        j = 1
        while j < record_len -i:
            if record[j - 1] > record[j]:
                compare = record[j - 1]
                record[j - 1] = record[j]
                record[j] = compare
            j += 1
        i += 1
    return record


def main():
    disordered_record = list(np.random.randint(-1, 100, 15))
    rd.shuffle(disordered_record)
    sorted_record = list_bubblesort(disordered_record[:])
    print('disordered list is:', disordered_record)
    print('sorted list is:', sorted_record)
    pass


if __name__ == '__main__':
    main()
