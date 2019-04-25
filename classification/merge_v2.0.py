#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/9/8 16:48

Description:
    基于地理坐标，对输入多个栅格影像进行镶嵌

Parameters
    in_files:merge file(file1,file2,file3...)
    out_file:out put file path(GTiff)
    nodata:nodata of input file(options)

"""

import os
import sys
import time
import tempfile

try:
    from osgeo import gdal, ogr
except ImportError:
    import gdal, ogr

try:
    progress = gdal.TermProgress_nocb
except:
    progress = gdal.TermProgress


def main(in_files, out_file, srcNodata, vrtNodata):
    vrt_file = os.path.join(tempfile.gettempdir(), '%s_vrt.vrt' % os.path.splitext(os.path.basename(out_file))[0])
    if os.path.exists(vrt_file):
        os.remove(vrt_file)

    gdal.BuildVRT(vrt_file, str(in_files).split(','), srcNodata=srcNodata, VRTNodata=vrtNodata)
    progress(0.25)
    out_driver = gdal.GetDriverByName("GTiff")

    if os.path.exists(out_file):
        out_driver.Delete(out_file)
        time.sleep(1)

    out_sds = out_driver.CreateCopy(out_file, gdal.Open(vrt_file))
    progress(0.85)

    out_sds = None

    os.remove(vrt_file)
    progress(1)


if __name__ == '__main__':
    start_time = time.time()

    #
    # if len(sys.argv[1:]) == 3:
    #     srcNodata = float(sys.argv[3])
    #     VRTNodata = float(sys.argv[3])
    # if len(sys.argv[1:]) == 2:
    #     srcNodata = 0
    #     VRTNodata = 0
    # if len(sys.argv[1:]) < 2:
    #     sys.exit('Problem reading input')

    # main(sys.argv[1], sys.argv[2])

    in_files = r"\\192.168.0.234\nydsj\project\11.邓州_正阳小麦\3.class_result\google\驻马店\google_20180418_zhengyang_class_res.tif," \
               r"\\192.168.0.234\nydsj\project\11.邓州_正阳小麦\3.class_result\GF2\驻马店\正阳\GF2_xiaomai_zhengyang.tif"
    out_file = r"\\192.168.0.234\nydsj\user\ZSS\test.tif"
    srcNodata = 200
    vrtNodata = 200
    main(in_files, out_file, srcNodata, vrtNodata)

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))
