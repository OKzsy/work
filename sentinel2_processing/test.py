#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2020/8/15 10:39
# @Author  : zhaoss
# @FileName: test.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:


Parameters


"""

import os
import sys
import glob
import time
import fnmatch
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress

vrt_options = gdal.BuildVRTOptions(resolution='user', xRes=10, yRes=10, separate=True,
                                   options=['-rb'])

print('end')
