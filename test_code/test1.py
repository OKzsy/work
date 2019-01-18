#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/12/19 18:20

Description:
    

Parameters
    

"""

import os
import sys
import time
import random
import string
import tempfile
import shutil
import psutil
import numpy as np
import numexpr as ne
import pandas as pd
import subprocess
import platform

try:
    from osgeo import gdal, ogr
except ImportError:
    import gdal, ogr

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def main():
    print('ok')


if __name__ == '__main__':
    start_time = time.time()

    # if len(sys.argv[1:]) < 2:
    #     sys.exit('Problem reading input')

    main()

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))