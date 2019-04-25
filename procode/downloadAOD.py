import requests
import json
import os


class RequestError(Exception):
    pass


class Nasa:
    def __init__(self, day=None, latlng=None, save_path=None):
        self.save_path = save_path
        self.headers = {
            'Host': 'ladsweb.modaps.eosdis.nasa.gov',
            'Referer': 'https://ladsweb.modaps.eosdis.nasa.gov/search/order/4/MOD04_L2--61/'
                       '2019-02-12/D/109.6,32.9,117.9,26.2',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/73.0.3683.75 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
        }
        self.url = "https://ladsweb.modaps.eosdis.nasa.gov/api/v1/files/" \
                   "product=MOD04_L2&collection=61&dateRanges={}&areaOfInterest={}&dayCoverage=true".format(day, latlng)

    def spider(self):
        resp = requests.get(url=self.url, headers=self.headers)
        if resp.status_code != 200:
            raise RequestError("请求错误,状态码为{}".format(resp.status_code))
        json_data = resp.json()
        for k, dic in json_data.items():
            name = dic["name"]
            lis = name.split(".")
            loc = lis[3][1:]
            year = lis[1].lstrip('A')[:4]
            code = lis[1].lstrip('A')[4:]
            file_url = "https://ladsweb.modaps.eosdis.nasa.gov/" \
                       "archive/allData/{}/MOD04_L2/{}/{}/{}".format(loc, year, code, name)
            print(file_url)
            resp = requests.get(url=file_url, headers=self.headers)
            path = os.path.join(self.save_path, name)
            with open(path, "wb") as f:
                f.write(resp.content)


if __name__ == '__main__':
    day = '2018-03-09'
    latlng = 'x110.3692y36.354952,x116.650994y31.400914'
    save_path = r"F:\henanxiaomai\new\20190223"
    instance = Nasa(day=day, latlng=latlng, save_path=save_path)
    instance.spider()
