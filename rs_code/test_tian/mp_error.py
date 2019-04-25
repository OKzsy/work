#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/12/21 10:42

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
from multiprocessing import Pool
try:
    from osgeo import gdal, ogr
except ImportError:
    import gdal, ogr

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress

from multiprocessing import Pool

def go():
    print(1)
    return np.zeros((2,3), dtype=np.int16)



def main():
    pool =Pool(processes=2)

    results = []
    for i in range(2):
        results.append(pool.apply_async(go, args=()))
        # pool.apply_async(go, args=()).get()
    pool.close()
    pool.join()

    for r in results:
        print(r.get())

    print('ok')


if __name__ == '__main__':
    start_time = time.time()

    # if len(sys.argv[1:]) < 2:
    #     sys.exit('Problem reading input')

    main()

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))