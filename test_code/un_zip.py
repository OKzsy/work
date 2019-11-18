#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Author: tianjg
Email:jango.tian@gmail.com
Create date: 2018/7/3 10:18

Description:
    对后缀为.gz和.zip的压缩文件包进行解压处理

Parameters
   in_file:压缩包文件路径
   out_dir:解压输出文件夹路径

"""
import datetime
import os
import re
import shutil
import zipfile
import tarfile
import gzip
import xml.dom.minidom as xmldom

try:
    from osgeo import gdal, ogr, osr
except ImportError:
    import gdal, ogr, osr


class WrongPath(BaseException):
    pass


def corner_to_geo(sample, line, dataset):
    """

    :param sample: 所计算点的列号
    :param line:   所计算点的行号
    :param dataset: 所计算影像的dataset
    :return: 所计算点的地理坐标
    """
    # 计算指定行,列号的地理坐标
    Geo_t = dataset.GetGeoTransform()
    # 计算地理坐标
    geoX = Geo_t[0] + sample * Geo_t[1]
    geoY = Geo_t[3] + line * Geo_t[5]
    return geoX, geoY


def corner(img_path):
    """

    :param data_ds: 所计算影像的dataset
    :return: 转换为经纬度的角点地理坐标
    """
    data_ds = gdal.Open(img_path)
    # 定义目标投影
    oSRS = osr.SpatialReference()
    oSRS.SetWellKnownGeogCS("WGS84")

    # 获取原始投影
    src_prj = data_ds.GetProjection()
    oSRC = osr.SpatialReference()
    oSRC.ImportFromWkt(src_prj)
    # 测试投影转换
    oSRC.SetTOWGS84(0, 0, 0)
    tx = osr.CoordinateTransformation(oSRC, oSRS)

    # 获取原始影像的放射变换参数
    geo_t = data_ds.GetGeoTransform()
    x_size = data_ds.RasterXSize  # Raster xsize
    y_size = data_ds.RasterYSize  # Raster ysize
    bandCount = data_ds.RasterCount  # Band Count
    dataType = data_ds.GetRasterBand(1).DataType  # Data Type
    # 获取影像的四个角点地理坐标
    # 左上
    old_ulx, old_uly = corner_to_geo(0, 0, data_ds)
    # 右上
    old_urx, old_ury = corner_to_geo(x_size, 0, data_ds)
    # 左下
    old_dlx, old_dly = corner_to_geo(0, y_size, data_ds)
    # 右下
    old_drx, old_dry = corner_to_geo(x_size, y_size, data_ds)

    # 计算出转换后角点的坐标（经纬度）
    # 左上
    (new_ulx, new_uly, new_ulz) = tx.TransformPoint(old_ulx, old_uly, 0)
    # 右上
    (new_urx, new_ury, new_urz) = tx.TransformPoint(old_urx, old_ury, 0)
    # 左下
    (new_dlx, new_dly, new_dlz) = tx.TransformPoint(old_dlx, old_dly, 0)
    # 右下
    (new_drx, new_dry, new_drz) = tx.TransformPoint(old_drx, old_dry, 0)
    # 统计出新影像的范围
    # 左上经度
    ulx = min(new_ulx, new_dlx)
    # 左上纬度
    uly = max(new_uly, new_ury)
    # 右下经度
    drx = max(new_urx, new_drx)
    # 右下纬度
    dry = min(new_dly, new_dry)
    # 右上经纬度
    urx = drx
    # 右上纬度
    ury = uly
    # 左下纬度
    dlx = ulx
    # 左下纬度
    dly = dry

    return "MULTIPOLYGON((({} {}, {} {}, {} {}, {} {}, {} {})))".format(ulx, uly, urx, ury, drx, dry, dlx, dly, ulx,
                                                                        uly)


def un_zipfile(zip_file, out_dir, satellite_id):
    with zipfile.ZipFile(zip_file, 'r') as fn:
        main = ""
        s = 0
        for file in fn.namelist():
            if s == 0:
                old_main_path = os.path.join(out_dir, file)
                try:
                    new_main_path = os.path.join(out_dir, file.encode('cp437').decode('utf8'))
                except Exception:
                    new_main_path = os.path.join(out_dir, file.encode('utf8').decode('utf8'))
                s += 1
            try:
                filename = file.encode('cp437').decode('utf8')  # 先使用cp437编码，然后再使用gbk解码
            except Exception:
                filename = file.encode('utf8').decode('utf8')
            tif = re.match(r'^.+?(?P<sensor>(PAN[12]|PAN|MSS[12]|MUX\d|MUX|AnalyticMS))\.(?P<tail>tiff|tif|img|rpb)$',
                           file)
            if tif:
                tail = tif.group("tail")
                if satellite_id != 5:
                    if tail == "rpb":
                        new_filename = os.path.splitext(filename)[0] + "_01.rpb"
                    else:
                        new_filename = os.path.splitext(filename)[0] + "_01.tiff"
                else:
                    new_filename = filename
            else:
                new_filename = filename

            new_path = os.path.join(out_dir, new_filename)
            if os.path.exists(new_path):
                continue
            else:
                fn.extract(file, out_dir)  # 解压缩ZIP文件
                os.chdir(out_dir)  # 切换到目标目录
                os.rename(file, new_filename)  # 重命名文件
        if os.path.exists(old_main_path):
            if not old_main_path == new_main_path:
                shutil.rmtree(main)


def un_tar(tar_file, out_dir):
    with tarfile.open(tar_file) as tar:
        tar_files = tar.getnames()
        for itar_file in tar_files:
            tif = re.match(r'^.+?(?P<sensor>(PAN[12]|PAN|MSS[12]|MUX[12]|MUX|AnalyticMS))\.(?P<tail>tiff|tif|img|rpb)$',
                           itar_file)
            if tif:
                sensor = tif.group("sensor")
                filename = re.sub(sensor, "{}_01".format(sensor), itar_file)
            else:
                filename = itar_file

            new_path = os.path.join(out_dir, filename)
            old_path = os.path.join(out_dir, itar_file)
            if os.path.exists(new_path):
                continue

            tar.extract(itar_file, out_dir)
            os.renames(old_path, new_path)

    os.remove(tar_file)


def un_gz(gz_file, out_dir):
    try:

        with gzip.open(gz_file, 'rb') as gz:
            gz_data = gz.read()

    except:
        print('Problem opening file %s !' % gz_file)
        return

    """ungz gz file"""
    out_file = os.path.normpath(os.path.join(out_dir, gz_file[:-3]))

    if os.path.isfile(out_file):
        os.remove(out_file)

    with open(out_file, 'wb') as out:
        out.write(gz_data)

    return out_file


def run_un_zip(in_file, out_dir, satellite_id):
    extension = os.path.splitext(os.path.basename(in_file))[1]

    if extension == '.gz':
        tar_file = un_gz(in_file, out_dir)
        un_tar(tar_file, out_dir)
    else:
        un_zipfile(in_file, out_dir, satellite_id)


def GET_XMLELEMENTS(oDocument, IDtxt):
    # 获取指定IDtxt的值
    oNodeList = oDocument.getElementsByTagName(IDtxt)
    # 定义返回的列表
    strDT = []
    if oNodeList.length == 1:
        return oNodeList[0].firstChild.data
    else:
        for node in oNodeList:
            strDT.append(node.firstChild.data)
        return strDT


def gf12(out_zip_dir, data, autotask_id):
    """gf2"""
    lis = []
    for path_name, dir_list, files_name in os.walk(out_zip_dir):
        for file in files_name:
            dic = {}
            tif = re.match(r'^.+(?P<sensor>(PAN[12]|PAN|MSS[12]|MUX\d|MUX))_01\.(tiff|tif|img)$', file)
            if tif:
                dic["sensor"] = tif.group("sensor")
                dic["origin_data_id"] = data["id"]
                dic["satellite_id"] = data["satellite_id"]
                dic["parent_names"] = [data["name"]]
                dic["name"] = file
                dic["path"] = os.path.join(path_name, dic["name"])
                # os.rename(os.path.join(path_name, file), dic["path"])
                xml_path = re.sub(r'_01\.(tiff|tif|img)$', r'.xml', dic["path"])
                xml = os.path.basename(xml_path)
                xml_obj = re.match(r'^GF1[BCD].*(PAN|MUX)[12].*$', xml)
                print(xml_path)
                print(xml_obj)
                print("*" * 50)
                if xml_obj:
                    # gf1 bcd三颗星中的PAN12,MUX12影像
                    s = 1
                    lines = []
                    with open(xml_path, "rb") as f:
                        for line in f:
                            if s >= 64 and s <= 71:
                                temp = line.decode("utf8").strip().replace("\\n", "")
                                postion = re.findall(r"\d+\.\d*", temp)
                                lines.append(postion[0])
                            s += 1
                    for n, i in enumerate(lines):
                        if n % 2 != 0:
                            temp = lines.pop(n)
                            lines.insert(n - 1, temp)
                    # 取时间
                    date = "%s000000" % os.path.basename(xml_path).split("_")[4]

                    dic["resolution"] = None
                    dic["min_date"] = date
                    dic["max_date"] = date
                    dic["the_geom"] = "MULTIPOLYGON((({} {},{} {},{} {},{} {},{} {})))".format(*lines, lines[0],
                                                                                               lines[1])
                else:
                    oDocument = xmldom.parse(xml_path).documentElement
                    # GF1,2
                    temp = "ImageGSD"
                    if len(GET_XMLELEMENTS(oDocument, temp)) == 0:
                        temp = "ImageGSDLine"
                    dic["resolution"] = round(float(GET_XMLELEMENTS(oDocument, temp)), 1)
                    temp = "ReceiveTime"
                    temp_time = GET_XMLELEMENTS(oDocument, temp).split(".")[0]
                    time = datetime.datetime.strptime(temp_time, "%Y-%m-%d %H:%M:%S")
                    new_time = time.strftime("%Y%m%d%H%M%S")
                    dic["min_date"] = new_time
                    dic["max_date"] = new_time
                    temp = "TopLeftLongitude"  # 左上经度 eg,112.913
                    ulx = GET_XMLELEMENTS(oDocument, temp)
                    temp = "TopLeftLatitude"  # 左上纬度 eg,34.6944
                    uly = GET_XMLELEMENTS(oDocument, temp)
                    temp = "TopRightLongitude"  # 右上经度 eg,113.161
                    urx = GET_XMLELEMENTS(oDocument, temp)
                    temp = "TopRightLatitude"  # 右上纬度 eg,34.6485
                    ury = GET_XMLELEMENTS(oDocument, temp)
                    temp = "BottomRightLongitude"  # 右下经度 eg, 113.105
                    drx = GET_XMLELEMENTS(oDocument, temp)
                    temp = "BottomRightLatitude"  # 右下纬度 eg, 34.4443
                    dry = GET_XMLELEMENTS(oDocument, temp)
                    temp = "BottomLeftLongitude"  # 左上经度 eg,112.858
                    dlx = GET_XMLELEMENTS(oDocument, temp)
                    temp = "BottomLeftLatitude"  # 左上经度 eg,34.4901
                    dly = GET_XMLELEMENTS(oDocument, temp)
                    dic["the_geom"] = "MULTIPOLYGON((({} {},{} {},{} {},{} {},{} {})))".format(ulx, uly, urx, ury,
                                                                                               drx, dry,
                                                                                               dlx, dly, ulx, uly)
                dic["dem"] = ""
                dic["aod"] = None
                dic["prj"] = ""
                dic["process"] = 1
                dic["autotask_id"] = autotask_id

                lis.append(dic)
    # process_dic = {"data": lis}
    return lis

def planet(out_zip_dir, data, autotask_id):
    lis = []
    for path_name, dir_list, files_name in os.walk(out_zip_dir):
        xml_dic = {}
        for file in files_name:
            dic = {}
            tif = re.match(r'^.+\.(tiff|tif)$', file)
            if tif:
                dic["origin_data_id"] = data["id"]
                dic["satellite_id"] = data["satellite_id"]
                dic["parent_names"] = [data["name"]]
                dic["name"] = file
                dic["path"] = os.path.join(path_name, dic["name"])
                if not xml_dic:
                    tif_xml = re.sub(r'(AnalyticMS_SR|AnalyticMS_DN_udm|AnalyticMS_01)\.(tiff|tif)$',
                                     r'AnalyticMS_metadata.xml', file)
                    xml_path = os.path.join(path_name, tif_xml)
                    print("xml_path=", xml_path)
                    oDocument = xmldom.parse(xml_path).documentElement
                    ID = 'eop:identifier'
                    img = GET_XMLELEMENTS(oDocument, ID)
                    xml_dic["sensor"] = img.split("_")[-1]
                    # dic["date"] = datetime.datetime.strptime("".join(img.split("_")[:2]), "%Y%m%d%H%M%S")
                    xml_dic["min_date"] = "".join(img.split("_")[:2])
                    xml_dic["max_date"] = "".join(img.split("_")[:2])
                    temp = "eop:resolution"
                    xml_dic["resolution"] = float(GET_XMLELEMENTS(oDocument, temp))
                    ID = 'ps:latitude'
                    latitude_lis = GET_XMLELEMENTS(oDocument, ID)
                    ID = 'ps:longitude'
                    longtitude_lis = GET_XMLELEMENTS(oDocument, ID)
                    coordinates = list(zip(longtitude_lis, latitude_lis))
                    coordinates.append(coordinates[0])
                    loc = ""
                    for coordinate in coordinates:
                        loc += "{} {}, ".format(coordinate[0], coordinate[1])
                    xml_dic["the_geom"] = "MULTIPOLYGON((({})))".format(loc[:-2])

                dic["sensor"] = xml_dic["sensor"]
                dic["min_date"] = xml_dic["min_date"]
                dic["max_date"] = xml_dic["max_date"]
                dic["resolution"] = xml_dic["resolution"]
                dic["the_geom"] = xml_dic["the_geom"]
                dic["dem"] = ""
                dic["aod"] = None
                dic["prj"] = ""
                dic["process"] = 1
                dic["autotask_id"] = autotask_id
                lis.append(dic)
    print("lis=", lis)
    # process_dic = {"data": lis}
    return lis


def uav(out_zip_dir, data, autotask_id):
    lis = []
    for path_name, dir_list, files_name in os.walk(out_zip_dir):
        for file in files_name:
            dic = {}
            tif = re.match(r'^UAV_(?P<date>\d+?)_.+?\.(tiff|tif)$', file)
            if tif:
                dic["origin_data_id"] = data["id"]
                dic["satellite_id"] = data["satellite_id"]
                dic["parent_names"] = [data["name"]]
                dic["name"] = file
                dic["path"] = os.path.join(path_name, dic["name"])
                dic["min_date"] = tif.group("date") + "000000"
                dic["max_date"] = tif.group("date") + "000000"
                dic["the_geom"] = corner(dic["path"])
                dic["process"] = 8
                dic["autotask_id"] = autotask_id
                dic["dem"] = ""
                dic["aod"] = None
                dic["prj"] = ""
                dic["resolution"] = None
                dic["sensor"] = ""
                lis.append(dic)
    print("lis=", lis)
    # process_dic = {"data": lis}
    return lis


def save_img(out_zip_dir, in_file, autotask_id):
    # 查询存储压缩影像
    name = os.path.basename(in_file)
    # temp1 = subprocess.check_output(
    #     ["python3", "/home/chronos/detection/manage.py", "handle_img", "--search", "origindata", name])
    # temp2 = base64.b64decode(temp1)
    # dic = json.loads(temp2.decode('utf-8'))

    from db.dbconnect import get_one, insert_lis
    dic = get_one("images_origindata", name)
    print("dic=", dic)
    if dic["satellite_id"] in [1, 2, 6, 7, 8]:  # GF1,GF2, GF1BCD
        process_lis = gf12(out_zip_dir, dic, autotask_id)
    if dic["satellite_id"] == 3:
        process_lis = planet(out_zip_dir, dic, autotask_id)
    if dic["satellite_id"] == 5:
        process_lis = uav(out_zip_dir, dic, autotask_id)
    insert_lis(process_lis)
    # origintifs = json.dumps(process_dic, ensure_ascii=False)
    # data = str(base64.b64encode(origintifs.encode("utf-8")), 'utf-8')
    # status = subprocess.call(["python3", "/home/chronos/detection/manage.py", "handle_img", "--save", data])
    # assert status == 0, "save data in database failed"

    # lis = []
    # for dic in process_dic["data"]:
    #     if not "SR" in dic["path"] and not "DN" in dic["path"]:
    #         lis.append(dic["path"])
    lis = []
    for dic in process_lis:
        if "SR" not in dic["path"] and "DN" not in dic["path"]:
            tif = re.match(r'^.+?GF1[BCD].+?(PAN|MUX)\d.+$', dic["path"])
            if not tif:
                lis.append(dic["path"])

    return lis


def main(*args, **kwargs):
    task_name = args[1]
    ti = kwargs['ti']
    path = ti.xcom_pull(key='path')
    # 异步任务id
    autotask_id = ti.xcom_pull(key='autotask_id')
    # 卫星id
    satellite_id = ti.xcom_pull(key='satellite_id')
    if path.endswith(".zip"):
        dirname = os.path.splitext(os.path.basename(path))[0]
    elif path.endswith(".tar.gz"):
        dirname = os.path.splitext(os.path.splitext(os.path.basename(path))[0])[0]
    else:
        raise WrongPath("please pass the correct path for un_zip process")
    if satellite_id == 5:
        uav_path = r"/mnt/glusterfs/change_detection/detection_image/uav"
        out_dir = os.path.join(uav_path, dirname)
    else:
        out_dir = os.path.join(kwargs["out"], dirname)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    run_un_zip(path, out_dir, satellite_id)
    lis = save_img(out_dir, path, autotask_id)

    kwargs['ti'].xcom_push(key=task_name, value=lis)

# if __name__ == '__main__':

# start_time = time.time()
#
# if len(sys.argv[1:]) < 2:
#     sys.exit('Problem reading input')
# # in_dir = r"D:\Data\Test_data\un_zip\in_dir"
# # out_dir = r"D:\Data\Test_data\un_zip\out_dir"
#
# in_file = sys.argv[1]
# out_dir = sys.argv[2]
# main(in_file, out_dir)
#
# end_time = time.time()
# print("time: %.2f min." % ((end_time - start_time) / 60))
