#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import glob
import time
import numpy as np
from scipy import optimize


# define function to calculate volume of box
def calcVolume(x):
    length = x[0]
    width = x[1]
    heigth = x[2]
    volume = length * width * heigth
    return volume


# define function to calculate surface area of box
def calcSurface(x):
    length = x[0]
    width = x[1]
    heigth = x[2]
    surfaceArea = 2 * length * width + 2 * length * heigth + 2 * width * heigth
    return surfaceArea


# define objective function for optimization
def objective(x):
    return -calcVolume(x)


# define constraint for optimization
def constraint(x):
    return 10 - calcSurface(x)


# load constaints into dictionary form
cons = ({'type': 'ineq', 'fun': constraint})

# set intial guess values for box dimensions
lengthGuess = 1
widthGuess = 1
heigthGuess = 1
# load guess values into numpy array
x0 = np.array([lengthGuess, widthGuess, heigthGuess])

# call solver to minimize the objective function given the constraints
sol = optimize.NonlinearConstraint(objective, x0, method='SLSQP', constraints=cons, options={'disp': True})

# retrieve optimized box sizing and volume
xOpt = sol.x
volumeOpt = -sol.fun


# calcultate surface area with optimized values just to double check
surfaceAreaOpt = calcSurface(xOpt)


# print results
print('length:' + str(xOpt[0]))
print('width:' + str(xOpt[1]))
print('volume:' + str(xOpt[2]))
print('surface Area:' + str(surfaceAreaOpt))


