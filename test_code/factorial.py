# -*- coding:utf-8 -*-

def cal_factorial(value):

    if value == 1:
        return 1
    else:
        return value * cal_factorial(value - 1)


def main():
    number = 13
    res = cal_factorial(number)
    print(res)
    return None


if __name__ == '__main__':
    main()
