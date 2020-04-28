#!/usr/bin/env python
# -*- coding:utf-8 -*-


import time


# Python中万物皆对象，即使是数字、字符串、函数、方法、类、模块
# 函数也是对象
def add(a, b):
    return a + b


def minus(a, b):
    return a - b


def print_start_and_end(func):
    # 定义一个既包含传入函数原有功能，又添加了新功能的函数
    def new_func(operation_func, operand_1, operand_2):
        print("{} start:{}".format(func.__name__, time.time()))
        # 运行传入函数
        func(operation_func, operand_1, operand_2)
        print("{} end:{}".format(func.__name__, time.time()))

    # 把这个新函数作为本函数返回值返回出去
    return new_func


# 实现计算器
# 第一个参数接受一个函数对象的引用
# 第二个第三个参数分别接受一个int或者float等类型的数字对象的引用
# calculator函数会试图将第一个参数标识符来调用这个函数
# 并将第二、三个标识符作为参数试图传入到第一个参数标识符指向的函数对象中去
@print_start_and_end
def calculator(operation_func, operand_1, operand_2):
    result = operation_func(operand_1, operand_2)
    print(result)


# 带参数装饰器
# 这是一个装饰器生成函数，执行他将得到一个装饰器
def print_start(should_remind_after_func_end=True):
    def decorate(func):
        def new_func():
            print("{} start:{}".format(func.__name__, time.time()))
            # 运行传入函数
            func()
            print("{} end:{}".format(func.__name__, time.time()))

        def new_func_without_end():
            print("{} start:{}".format(func.__name__, time.time()))
            # 运行传入函数
            func()

        if should_remind_after_func_end:
            return new_func
        else:
            return new_func_without_end

    # 返回装饰器
    return decorate


@print_start(should_remind_after_func_end=True)
def myFunc():
    print("I am myFunc")


def main():
    # =====================开始调用==================

    # myFunc = print_start(should_remind_after_func_end=True)(myFunc)
    myFunc()
    pass


if __name__ == '__main__':
    main()
    pass
