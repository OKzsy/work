#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import glob
import time
import numpy as np
from scipy.optimize import minimize
from scipy.optimize import LinearConstraint

# Create initial point.

x0 = [.1, .1]


# Create function to be minimized

def obj(x):
    return x[0] + x[1]


# Create linear constraints  lbnd<= A*
# (x,y)^T<= upbnd

A = [[1, 0], [0, 1]]

lbnd = [0, 0]

upbnd = [1, 1]

lin_cons = LinearConstraint(A, lbnd, upbnd)

sol = minimize(obj, x0, constraints=lin_cons)

print(sol)
