#!/usr/bin/env python
# -*- coding:utf-8 -*-

import numpy as np

Matrix = [[10, 1, 2], [3, 15, 4], [5, 6, 20]]
mat = np.array(Matrix)
flags = ['猫', '狗', '猪']
micro_ppv = np.zeros(len(flags))
micro_trp = np.zeros(len(flags))
for iflag in range(len(flags)):
    Tp = mat[iflag, iflag]
    Fp = np.sum(mat[iflag, :]) - Tp
    Fn = np.sum(mat[:, iflag]) - Tp
    Tn = np.sum(mat) - Tp - Fp - Fn

    acc = np.trace(mat) / (Tp + Fp + Fn + Tn)
    ppv = Tp / (Tp + Fp)
    micro_ppv[iflag] = ppv
    trp = Tp / (Tp + Fn)
    micro_trp[iflag] = trp
    tnr = Tn / (Fp + Tn)
    F1Score = 2 * ppv * trp / (ppv + trp)
    print('The flag is: {}'.format(flags[iflag]))
    print('The Accuracy is: {}'.format(acc))
    print('The Precision is: {}'.format(ppv))
    print('The Sensitivity is: {}'.format(trp))
    print('The Specificity is: {}'.format(tnr))
    print('The F1-Score is: {}'.format(F1Score))
micro_p = np.average(micro_ppv)
micro_t = np.average(micro_trp)
micro_f1 = 2 * micro_p * micro_t / (micro_p + micro_t)
print('The Micro-F1-Score is: {}'.format(micro_f1))
# 计算kappa系数
pe_rows = np.sum(mat, axis=0)
pe_cols = np.sum(mat, axis=1)
sum_total = sum(pe_cols)
pe = np.dot(pe_rows, pe_cols) / float(sum_total ** 2)
po = np.trace(mat) / float(sum_total)
kappa = (po - pe) / (1 - pe)
print('The Kappa is: {:<5.4}'.format(kappa))