#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Author:zhaoss
Email:zhaoshaoshuai@hnnydsj.com
Create date:  
File: .py
Description:


Parameters


"""
import sys
from osgeo import ogr


fn = r"E:\osgeopy-data\global\ne_50m_populated_places.shp"
ds = ogr.Open(fn, 0)
if ds is None:
    sys.exit('Could not open {0]'.format(fn))
lyr = ds.GetLayer(0)

i = 0
for feat in lyr:
    pt = feat.geometry()
    x = pt.GetX()
    y = pt.GetY()
    name = feat.GetField('NAME')
    pop = feat.GetField('POP_MAX')
    print(name, pop, x, y)
    i += 1
    if i == 10:
        break
del ds





