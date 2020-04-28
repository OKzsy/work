#!/usr/bin/env python
# -*- coding:utf-8 -*-


def my_generator(n):
    for i in range(n):
        temp = yield i
        # print(f'我是{temp}')

g = my_generator(5)

print(next(g))
print(next(g))
g.send(100)
print(next(g))
