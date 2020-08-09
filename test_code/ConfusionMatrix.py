#!/usr/bin/env python
# -*- coding:utf-8 -*-

import numpy as np

Matrix = [[10, 1, 2], [3, 15, 4], [5, 6, 20]]
mat = np.array(Matrix)
flags = ['猫', '狗', '猪']
for iflag in range(len(flags)):
    Tp = mat[iflag, iflag]
    Fp = np.sum(mat[iflag, :]) - Tp
    Fn = np.sum(mat[:, iflag]) - Tp
    Tn = np.sum(mat) - Tp - Fp - Fn

    acc = np.trace(mat) / (Tp + Fp + Fn + Tn)
    ppv = Tp / (Tp + Fp)
    trp = Tp / (Tp + Fn)
    tnr = Tn / (Fp + Tn)
    F1Score = 2 * ppv * trp / (ppv + trp)
    print('The flag is: {}'.format(flags[iflag]))
    print('The Accuracy is: {}'.format(acc))
    print('The Precision is: {}'.format(ppv))
    print('The Sensitivity is: {}'.format(trp))
    print('The Specificity is: {}'.format(tnr))
    print('The F1-Score is: {}'.format(F1Score))
