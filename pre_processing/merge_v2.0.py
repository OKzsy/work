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


def main(in_files, out_file):

    vrt_file = os.path.join(tempfile.gettempdir(), '%s_vrt.vrt' % os.path.splitext(os.path.basename(out_file))[0])
    if os.path.exists(vrt_file):
        os.remove(vrt_file)

    # gdal.BuildVRT(vrt_file, str(in_files).split(','), srcNodata = srcNodata, VRTNodata = VRTNodata)
    gdal.BuildVRT(vrt_file, str(in_files).split(','), srcNodata = srcNodata, VRTNodata = VRTNodata)
    # gdal.BuildVRT(vrt_file, str(in_files).split(','))
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
    if len(sys.argv[1:]) == 3:
        srcNodata = float(sys.argv[3])
        VRTNodata = float(sys.argv[3])
    if len(sys.argv[1:]) == 2:
        srcNodata = 0
        VRTNodata = 0
    if len(sys.argv[1:]) < 2:
        sys.exit('Problem reading input')

    main(sys.argv[1], sys.argv[2])

    # in_files = r'D:\Data\Test_data\out_s2_luoyang\Sub_ref\S2A_MSIL2A_20180725T031541_N0206_R118_T49SET_20180725T061658\L2A_T49SET_A016131_20180725T032152_ref_10m.tif,' \
    #            r'D:\Data\Test_data\out_s2_luoyang\Sub_ref\S2A_MSIL2A_20180725T031541_N0206_R118_T49SEU_20180725T061658\L2A_T49SEU_A016131_20180725T032152_ref_10m.tif'
    # out_file = r"D:\Data\Test_data\mosaic_20180908\in_file_list_txt_mosaic.tif"
    # srcNodata = 0
    # VRTNodata = 0
    # main(in_files, out_file)

    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))