#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import glob
import time
import shutil
import re


def main():
    file = r"F:\xml"
    res = glob.glob(os.path.join(file, "*2018*.xml"))
    basename = re.split('_|-', os.path.splitext(os.path.basename(res[0]))[0])
    print(basename)


if __name__ == '__main__':
    start_time = time.clock()

    main()

    end_time = time.clock()

    print("time: %.9f sec." % ((end_time - start_time)))
