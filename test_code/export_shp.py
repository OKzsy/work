import sys
from osgeo import ogr

# 打开要写入的数据源
ds = ogr.Open(r'E:\osgeopy-data\global', 1)
if ds is None:
    sys.exit('Could not open folder.')
# 获取shapefile文件
in_lyr = ds.GetLayer('ne_50m_populated_places')

# 创建要导出的图层，如果存在就删除
if ds.GetLayer('capital_cities'):
    ds.DeleteLayer('capital_cities')
out_lyr = ds.CreateLayer('capital_cities',
                         in_lyr.GetSpatialRef(),
                         ogr.wkbPoint)
# 创建字段(类似于创建表头）
out_lyr.CreateFields(in_lyr.schema)
# 创建一个空要素
out_defn = out_lyr.GetLayerDefn()
out_feat = ogr.Feature(out_defn)
for in_feat in in_lyr:
    if in_feat.GetField('FEATURECLA') == 'Admin-0 capital':
        geom = in_feat.geometry()
        out_feat.SetGeometry(geom)
        for i in range(in_feat.GetFieldCount()):
            value = in_feat.GetField(i)
            out_feat.SetField(i, value)
        out_lyr.CreateFeature(out_feat)
del ds
