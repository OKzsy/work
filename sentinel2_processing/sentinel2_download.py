#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2023/2/28 18:04
# @Author  : zhaoss
# @FileName: sentinel2_download.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
哨兵数据下载程序

Parameters

"""
import os
import sys
import time
import requests
import requests.exceptions as exception
import xml.etree.ElementTree as ET
from requests.auth import HTTPBasicAuth
from requests.adapters import HTTPAdapter
import multiprocessing.dummy as mp
from urllib3 import Retry
import http

# debug
http.client.HTTPConnection.debuglevel = 0
# timeout
DEFAULT_TIMEOUT = 60  # seconds
# raise error for 4xx,5xx
assert_status_hook = lambda response, * \
    args, **kwargs: response.raise_for_status()

retry_strategy = Retry(
    total=5,
    backoff_factor=0.1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS"]
)
# adapter = HTTPAdapter(max_retries=retry_strategy)

headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Host": "scihub.copernicus.eu",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "Windows",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
}


class TimeoutHTTPAdapter(HTTPAdapter):
    def __init__(self, *args, **kwargs):
        self.timeout = DEFAULT_TIMEOUT
        if "timeout" in kwargs:
            self.timeout = kwargs["timeout"]
            del kwargs["timeout"]
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        timeout = kwargs.get("timeout")
        if timeout is None:
            kwargs["timeout"] = self.timeout
        return super().send(request, **kwargs)


def BuildOptions(platformname='Sentinel-2',
                 tile=None,
                 begintime=None,
                 endtime=None,
                 filename=None,
                 footprint=None,
                 producttype='S2MSI1C',
                 cloud=100,
                 page_size=50,
                 page_start_value=0):
    options = []
    # 页面配置
    if page_start_value is not None:
        options += ['start=' + str(page_start_value)]
    if page_size is not None:
        options += ['rows=' + str(page_size)]
    # 查询关键字
    query = []
    if tile is not None:
        query += [tile]
    if footprint is not None:
        tmp_str = '(footprint:"Intersects(POLYGON((' + footprint + ')))")'
        query += [tmp_str]
    if filename is not None:
        query += ['filename:' + filename]
    query1 = []
    if begintime is None:
        begintime = 'NOW-6MONTHS TO '
    else:
        begintime = begintime + 'T00:00:00.000Z TO '
    if endtime is None:
        endtime = 'NOW'
    else:
        endtime = endtime + 'T23:59:59.999Z'
    query1 += ['beginPosition:' + '[' + begintime + endtime + ']']
    query1 += ['endPosition:' + '[' + begintime + endtime + ']']
    query1_combine = ' AND '.join(query1)
    query += ['(' + query1_combine + ')']
    query2 = []
    if platformname is not None:
        query2 += ['platformname:' + platformname]
    if producttype is not None:
        query2 += ['producttype:' + producttype]
    if filename is not None:
        query2 += ['filename:' + filename]
    if cloud is not None:
        query2 += ['cloudcoverpercentage:' +
                   '[' + '0' + ' TO ' + str(cloud) + ']']
    query2_combine = ' AND '.join(query2)
    query += ['(' + query2_combine + ')']
    query_combine = 'q=' + ' AND '.join(query)
    options += [query_combine]
    options_combine = '&'.join(options)
    return options_combine


def parse_xml(root, flag, attri=None, attri_value=None, namespace=None):
    # 判断获取的数据内容
    flag_name = flag.split(':')[1]
    # 匹配节点
    if flag_name == 'entry':
        allMetadatas = {}
        for node in root.findall(flag, namespace):
            # 获取日期
            for date in node.findall('root:date', namespace):
                attrib_lst = date.items()
                if attrib_lst[0][1] == 'datatakesensingstart':
                    date_str = date.text.split('T')[0]
                    break
            if date_str not in list(allMetadatas.keys()):
                allMetadatas[date_str] = []
            metadata = {}
            # 获取数据编号
            for tile in node.findall('root:str', namespace):
                attrib_lst = tile.items()
                if attrib_lst[0][1] == 'tileid':
                    tileid = tile.text
                    break
            metadata['tileid'] = tileid
            # 获取云含量
            clodecoverage = node.find('root:double', namespace).text
            metadata['cloudcover'] = clodecoverage
            # 获取矢量多边形
            for polygon in node.findall('root:str', namespace):
                attrib_lst = polygon.items()
                if attrib_lst[0][1] == 'footprint':
                    polygon_str = polygon.text.split('(')[-1][:-3]
                    break
            metadata['boundary'] = polygon_str
            # 获取文件名
            file_name = node.find('root:title', namespace).text
            metadata['filename'] = file_name
            # 获取数据链接
            for link in node.findall('root:link', namespace):
                attrib_lst = link.items()
                attrib_num = len(attrib_lst)
                if attrib_num == 1:
                    data_link = attrib_lst[0][1]
                    metadata['dataLink'] = data_link
                elif attrib_lst[0][1] == 'icon':
                    quicklook_link = attrib_lst[1][1]
                    metadata['viewLink'] = quicklook_link
            allMetadatas[date_str].append(metadata)
        return allMetadatas
    else:
        content = []
        for node in root.findall(flag, namespace):
            if attri:
                if node.attrib[attri] == attri_value:
                    pass
            else:
                content.append(node.text)
                pass
    return content


def progress(percent, name=None, netSpeed=None, width=50):
    if percent >= 1:
        percent = 1
    fmt = '[{{:<{}}}]'.format(width)
    show_str = fmt.format(int(width*percent)*'#')
    if name is not None:
        print('\r{0} {1:>3.0%}-{2:>7.3f} M/s {3}'.format(show_str,
                                                         percent, netSpeed, name), file=sys.stdout, flush=True, end='')
    else:
        print('\r{0} {1:>3.0%}-{2:>7.3f} M/s'.format(show_str,
                                                     percent, netSpeed), file=sys.stdout, flush=True, end='')


def download(url, dst, limit=10):
    basename = os.path.basename(dst)
    # 创建会话
    http = requests.Session()
    http.hooks["response"] = [assert_status_hook]
    http.mount("https://", TimeoutHTTPAdapter(max_retries=retry_strategy))
    http.mount("http://", TimeoutHTTPAdapter(max_retries=retry_strategy))
    # 创建会话，获取文件大小
    try:
        respons1 = http.get(url, headers=headers, stream=True, auth=HTTPBasicAuth(
            username='hpu_zss', password='120503xz'))
    except exception.RequestException as e:
        http.close()
        print('无法获取 {0} 的链接,原因如下：'.format(basename))
        print(e)
        return None
    # print(respons1.status_code)
    # 文件总大小
    total_size = int(respons1.headers['content-length'])
    # 获取目标文件是否存在，存在则获取大小
    if os.path.exists(dst):
        temp_size = os.path.getsize(dst)
    else:
        temp_size = 0
    if temp_size >= total_size:
        http.close()
        print('{} is already download!'.format(basename))
        return None
    else:
        # 重复尝试下载
        retry_count = 0
        while retry_count < limit:
            if retry_count > 0:
                temp_size = os.path.getsize(dst)
            if temp_size >= total_size:
                http.close()
                return None
            print('{}, retry_count:{}'.format(basename, retry_count))
            retry_count += 1
            # 下载数据
            header = {'Range': 'bytes={0}-'.format(str(temp_size))}
            try:
                respons2 = http.get(url, headers=header, stream=True)
            except exception.RequestException as e:
                http.close()
                print('无法获取 {0} 的链接,原因如下：'.format(basename))
                print(e)
                continue
            start_time = time.time()
            with open(dst, 'ab') as f:
                speed_low_count = 0
                for chunk in respons2.iter_content(chunk_size=1024*512):
                    if chunk:
                        count_temp = len(chunk)
                        temp_size += count_temp
                        mid_time = time.time()
                        speed = (count_temp) / 1024 / 1024 / \
                            (mid_time - start_time + 0.00001)
                        start_time = mid_time
                        percent = temp_size / total_size
                        f.write(chunk)
                        f.flush()
                        # 网速持续过慢, 结束进程
                        if speed < 0.001:
                            speed_low_count += 1
                        else:
                            speed_low_count = 0
                        if speed_low_count >= 5:
                            print(
                                '{}-speed_low_count: {}, speed: {}'.format(basename, speed_low_count, speed))
                            http.close()
                            break
                        # progress(percent=percent, name=basename, netSpeed=speed)
            if retry_count == limit:
                http.close()
        http.close()
        time.sleep(2)
    return None


def spatialfilter(farmshapefile, allDataDict, high=['49SGV']):
    from osgeo import gdal, ogr
    needData = {}
    needData['Name'] = []
    needData['dataLink'] = []
    needData['viewLink'] = []
    # 获取农场的范围
    inDriver = ogr.GetDriverByName("ESRI Shapefile")
    inDataSource = inDriver.Open(farmshapefile, 0)
    inLayer = inDataSource.GetLayer()
    for feat in inLayer:
        geom = feat.geometry().Clone()
        # 逐个对比待下载数据
        for date, data in allDataDict.items():
            dataName = []
            dataLink = []
            quickviewLink = []
            # 判断是否存在优先下载的数据
            if high:
                alltileid = [k['tileid'] for k in data]
                highRank = [k for k in alltileid if k in high]
            else:
                highRank = None
            # 获取有效数据的矢量范围
            cloud = 100
            for tmpData in data:
                boundary = tmpData['boundary'].split(',')
                # 创建多边形
                ring = ogr.Geometry(ogr.wkbLinearRing)
                for point in boundary:
                    lon, lat = map(float, point.split())
                    ring.AddPoint(lon, lat)
                poly = ogr.Geometry(ogr.wkbPolygon)
                poly.AddGeometry(ring)
                poly.CloseRings()
                tileid = tmpData['tileid']
                # 进行对比并放入带下载数据列表
                if poly.Contains(geom):
                    if highRank:
                        if tileid in highRank:
                            tempcloud = float(tmpData['cloudcover'])
                            if tempcloud <= cloud:
                                dataLink.clear()
                                dataName.clear()
                                quickviewLink.clear()
                                dataName.append(tmpData['filename'])
                                dataLink.append(tmpData['dataLink'])
                                quickviewLink.append(tmpData['viewLink'])
                            cloud = tempcloud
                    else:
                        tempcloud = float(tmpData['cloudcover'])
                        if tempcloud <= cloud:
                            dataLink.clear()
                            dataName.clear()
                            quickviewLink.clear()
                            dataName.append(tmpData['filename'])
                            dataLink.append(tmpData['dataLink'])
                            quickviewLink.append(tmpData['viewLink'])
                        cloud = tempcloud
                else:
                    dataName.append(tmpData['filename'])
                    dataLink.append(tmpData['dataLink'])
                    quickviewLink.append(tmpData['viewLink'])
                poly.Destroy()
            needData['Name'] += dataName
            needData['dataLink'] += dataLink
            needData['viewLink'] += quickviewLink
        feat.Destroy()
    inLayer = inDataSource = None
    return needData


def getPoints(farmshapefile):
    from osgeo import gdal, ogr
    # 获取农场的范围
    inDriver = ogr.GetDriverByName("ESRI Shapefile")
    inDataSource = inDriver.Open(farmshapefile, 0)
    inLayer = inDataSource.GetLayer()
    for feat in inLayer:
        geom = feat.geometry().Clone()
        polygon = geom.GetGeometryRef(0)
        coorPoints = polygon.GetPoints()
        footprint = ','.join(list(map(lambda x: ' '.join(
            list(map(str, [x[0], x[1]]))), [k for k in coorPoints])))
        feat.Destroy()
    return footprint


def main(roi):
    # 获取农场范围
    coordinate = getPoints(roi)
    # 创建查询条件
    res = BuildOptions(footprint=coordinate)
    # 查询数据
    base_url = 'https://scihub.copernicus.eu/dhus/search?'
    url = base_url + res
    http = requests.Session()
    http.hooks["response"] = [assert_status_hook]
    http.mount("https://", TimeoutHTTPAdapter(max_retries=retry_strategy))
    http.mount("http://", TimeoutHTTPAdapter(max_retries=retry_strategy))
    try:
        html = http.get(url, headers=headers, auth=HTTPBasicAuth(
            username='hpu_zss', password='120503xz'))
    except exception.RequestException as e:
        http.close()
        print("无法获取数据链接，原因如下：")
        print(e)
        sys.exit(0)
    # 获取数据列表
    xmlroot = ET.fromstring(html.text)
    http.close()
    # 去除命名空间的影响
    ns = {"opensearch": "http://a9.com/-/spec/opensearch/1.1/",
          "root": "http://www.w3.org/2005/Atom"}
    # 获取数据个数
    total_imgs = parse_xml(xmlroot, 'opensearch:totalResults', namespace=ns)
    # 获取数据名称,数据链接,快视图链接
    alldata = parse_xml(xmlroot, 'root:entry', namespace=ns)
    # 筛选需要下载的数据
    vaildDatas = spatialfilter(roi, alldata)
    # 下载数据
    jobs = 2
    pool = mp.Pool(processes=jobs)
    for i in range(len(vaildDatas['Name'])):
        name = vaildDatas['Name'][i]
        url = vaildDatas['viewLink'][i]
        dst = os.path.join(r'F:\test\S2\view', name) + '.jpg'
        # download(url, dst)
        pool.apply_async(download, args=(url, dst,))
    pool.close()
    pool.join()
    # name = file_names[i]
    # url = data_links[i]
    # dst = os.path.join(r'F:\test\S2', name) + '.zip'
    # res = download(url, dst)
    # if res:
    #     print('{} is already download!'.format(res))
    # else:
    #     print(end='\n')
    return None


if __name__ == '__main__':
    # 待抓取地区的网址
    start_time = time.time()
    # 农场边界
    roi = r"F:\tmp\farm\farm.shp"
    main(roi)
    end_time = time.time()
    print("time: %.2f min." % ((end_time - start_time) / 60))
