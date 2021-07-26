#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2021/3/30 14:55
# @Author  : zhaoss
# @FileName: create_colorbar.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
import matplotlib as mpl
from matplotlib.colors import ListedColormap, LinearSegmentedColormap
import time


def plot_examples(colormaps):
    """
    Helper function to plot data with associated colormap.
    """
    np.random.seed(19680801)
    data = np.random.randn(30, 30)
    n = len(colormaps)
    fig, axs = plt.subplots(1, n, figsize=(n * 2 + 2, 3),
                            constrained_layout=True, squeeze=False)
    for [ax, cmap] in zip(axs.flat, colormaps):
        psm = ax.pcolormesh(data, cmap=cmap, rasterized=True, vmin=-4, vmax=4)
        fig.colorbar(psm, ax=ax)
    plt.show()


def main():
    # 解决中文乱码
    plt.rcParams['font.sans-serif'] = ['SimHei']
    plt.rcParams['axes.unicode_minus'] = False
    # 自定义颜色
    N = 256
    vals = np.ones((N, 4))
    vals[:, 0] = np.linspace(90 / 256, 1, N)
    vals[:, 1] = np.linspace(40 / 256, 1, N)
    vals[:, 2] = np.linspace(40 / 256, 1, N)
    newcmp = ListedColormap(vals)

    fig = plt.figure(figsize=(1, 6.0))
    ax = fig.add_axes((0.3, 0.1, 0.3, 0.8))
    # 绘制colorbar
    cb1 = mpl.colorbar.ColorbarBase(ax, cmap=newcmp,
                                    extend='both',
                                    orientation='vertical')
    cb1.ax.set_title('土壤旱情', loc='center')
    cb1.set_ticks(np.linspace(0, 1, 5, endpoint=True))
    cb1.set_ticklabels(["无旱", "轻旱", "中旱", "重旱", "特旱"])
    plt.savefig(r"F:\test\colorbar.png", transparent=True)
    return None


if __name__ == '__main__':
    start_time = time.time()

    main()
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
