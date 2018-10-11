import fnmatch

name = "GF1_PMS1_E113.2_N33.9_20170713_L1A0002482515-MSS1.xml"

res = fnmatch.fnmatch(name, "*.xml")
print(res)
