#!/usr/bin/env python
# -*- coding:utf-8 -*-

import numpy as np
from scipy.interpolate import interp1d
import pylab as pl

# 创建待插值的数据
x = np.arange(61)/10 -3
y = np.sin(x)

# 分别用linear和quadratic插值
# fl = interp1d(x, y, kind='linear')
fq = interp1d(x, y, kind='quadratic')

# 设置x的最大值和最小值以防止插值数据越界
xint = np.arange(50)/10 - 2.35
# yintl = fl(xint)
yintq = fq(xint)
print(yintq)


pl.plot(x, y, color="green", label="original")
# pl.plot(xint, fl(xint), color="green", label="Linear", marker='*', ms=10)
pl.plot(xint, fq(xint), color="yellow", label="Quadratic", marker='1', ms=10)
pl.legend(loc="best")
pl.show()
