# -*- coding:utf-8 -*-


def recursion_sum(num):
    if num == 1:
        return 1
    tt = recursion_sum(num - 1) + num
    print('第{}次递归'.format(num))
    print('返回值{}在内存中的地址:{}'.format(tt, id(tt)))
    return tt


print(recursion_sum(10))