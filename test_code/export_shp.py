import sys
from osgeo import ogr

ogr.UseExceptions()

# # 打开要写入的数据源
# ds = ogr.Open(r'F:\geoprocessing-with-python\global', 1)
# if ds is None:
#     sys.exit('Could not open folder.')
# # 获取shapefile文件
# in_lyr = ds.GetLayer('ne_50m_populated_places')
#
# # 创建要导出的图层，如果存在就删除
# if ds.GetLayer('capital_cities'):
#     ds.DeleteLayer('capital_cities')
# out_lyr = ds.CreateLayer('capital_cities',
#                          in_lyr.GetSpatialRef(),
#                          ogr.wkbPoint)
# # 创建字段(类似于创建表头）
# out_lyr.CreateFields(in_lyr.schema)
# coord_fid = ogr.FieldDefn('X', ogr.OFTReal)
# coord_fid.SetWidth(8)
# coord_fid.SetPrecision(3)
# out_lyr.CreateField(coord_fid)
# coord_fid.SetName('Y')
# out_lyr.CreateField(coord_fid)
# # 创建唯一ID
# id_fid = ogr.FieldDefn('ID', ogr.OFTInteger)
# out_lyr.CreateField(id_fid)
# # 更改字段名称
# i = out_lyr.GetLayerDefn().GetFieldIndex('Name')
# fld_Def = ogr.FieldDefn('City_Name', ogr.OFTString)
# out_lyr.AlterFieldDefn(i, fld_Def, ogr.ALTER_NAME_FLAG)
# # 创建虚拟空要素
# out_defn = out_lyr.GetLayerDefn()
# out_feat = ogr.Feature(out_defn)
# n = 1
# for in_feat in in_lyr:
#     if in_feat.GetField('FEATURECLA') == 'Admin-0 capital':
#         geom = in_feat.geometry()
#         out_feat.SetGeometry(geom)
#         # 写入属性信息
#         for i in range(in_feat.GetFieldCount()):
#             value = in_feat.GetField(i)
#             out_feat.SetField(i, value)
#         out_feat.SetField('ID', n)
#         n += 1
#         out_lyr.CreateFeature(out_feat)
# ds.SyncToDisk()
# del ds
ds = ogr.Open(r"F:\geoprocessing-with-python\global\capital_cities.shp", 1)
lyr = ds.GetLayer(0)
# 剔除假删除要素，回收空间
ds.ExecuteSQL('REPACK ' + lyr.GetName())
# 更新数据范围
ds.ExecuteSQL('RECOMPUTE EXTENT ON ' + lyr.GetName())
print('hello')
