#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""该程序用于计算儒略日"""

import datetime


class Julday:

    def __init__(self, year, month, day):
        self.year = int(year)
        self.month = int(month)
        self.day = int(day)

    def cal_julday(self):
        # 利用datetime库中的datetime函数的方法快速计算需要日期的儒略日
        current = datetime.datetime(self.year, self.month, self.day)
        re_julday = current.timetuple().tm_yday
        return re_julday


jul = Julday('2017', '10', '20')
re = jul.cal_julday()

print(re)
