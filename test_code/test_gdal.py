#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import glob
import time
from osgeo import gdal

vrt_options = gdal.BuildVRTOptions(resolution='user', xRes=10, yRes=10, separate=True,
                                           resampleAlg=gdal.GRA_Bilinear)
print('end')