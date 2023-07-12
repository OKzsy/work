import random
import re
 
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import os
import requests
import parsel
import threading
from selenium import webdriver
 
 
# 模特
class Model():
    # 模特姓名
    model_name = ''
    # 模特主页地址
    model_url = ''
 
 
# 相册
class Album():
    name = ''
    url = ''
    # 相册里面多少张照片
    page = ''
 
 
# 请求
def url_request(url):
    headers = {
        'cookie': 'Hm_lvt_86200d30c9967d7eda64933a74748bac=1654084589; Hm_lpvt_86200d30c9967d7eda64933a74748bac=1654084589; t=dd9f5522044817b834289648b9a38ecc; r=8839',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.0.0 Safari/537.36'
    }
    # print("请求网址：" + url)
    response = requests.get(url=url, headers=headers)  # <Response [200]> 返回响应对象 200状态码标识请求成功
    selector = parsel.Selector(response.text)
    response.close()
    return selector
 
 
# 获取model对象的集合
def get_model_url():
    # 首页
    main_url = f'https://mmzztt.com/photo/model/'
    sel = url_request(main_url)
    model_name_lists = sel.xpath('//h2[@class="uk-card-title uk-margin-small-top uk-text-center"]/a/text()').getall()
    model_url_lists = sel.xpath('//h2[@class="uk-card-title uk-margin-small-top uk-text-center"]/a/@href').getall()
    mode_list = []
    for (name, url) in zip(model_name_lists, model_url_lists):
        model = Model()
        model.model_name = name
        model.model_url = url
        mode_list.append(model)
    return mode_list
 
 
# 创建浏览器对象
def creat_chrome_driver(*, headless=False):
    # options = webdriver.ChromeOptions()
    # if headless:
    #     options.add_argument('--headless')
    # options.add_argument('--no-sandbox')
    # options.add_argument('--disable-dev-shm-usage')
    # # options.add_argument('blink-settings=imagesEnabled=false')
    # options.add_argument('--disable-gpu')
    # options.add_argument("--disable-blink-features")
    # options.add_argument("--disable-blink-features=AutomationControlled")
    # options.add_experimental_option("excludeSwitches", ['enable-automation'])
    # options.add_experimental_option('useAutomationExtension', False)
    # browser = webdriver.Chrome(executable_path='/robot/driver/chromedriver', options=options)
    # browser.execute_cdp_cmd(
    #     'Page.addScriptToEvaluateOnNewDocument',
    #     {'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'}
    # )
    chrome_options = Options()
    # chrome_options.add_argument("--headless=new")
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('log-level=3')
    chrome_options.add_argument(
        r'--user-data-dir=C:\Users\01\AppData\Local\Google\Chrome\User Data\Default')
    # 开启静默模式
    browser = webdriver.Chrome(options=chrome_options)
    return browser


# 下载图片
def download_iamge(image_url, path, picture_name):
    headers2 = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.0.0 Safari/537.36',
        'Referer': "https://mmzztt.com/",
        'If-None-Match': 'f9d99da9fd3d18566e2089720850ef70',
    }
    print("图片地址："+ image_url)
    response2 = requests.get(url=image_url, headers=headers2)
    response2.close()
    time.sleep(0.4)
    new_path = path + "/" + str(picture_name) + '.jpg'
    with open(new_path, mode='wb') as f:
        f.write(response2.content)
 
if __name__ == '__main__':
    path1 = r'E:\FarmMmonitor\data'
    model_list = get_model_url()
 
    # 获得浏览器对象1
    driver1 = creat_chrome_driver()
    driver1.maximize_window()
 
    for model in model_list:
        print('模特名：', model.model_url)
        print('模特主页地址', model.model_name)
 
        driver1.get(model.model_url)
        time.sleep(1)
 
        # 此model的相册集合
        album_list = []
        current_url = url_request(driver1.current_url)
        album_name_list = current_url.xpath('//h2[@class="uk-card-title uk-margin-small-top uk-margin-remove-bottom"]/a/text()').getall()
        album_url_list = current_url.xpath('//h2[@class="uk-card-title uk-margin-small-top uk-margin-remove-bottom"]/a/@href').getall()
        album_page_list = current_url.xpath('//div[@class="uk-card-badge uk-label u-label"]/text()').getall()
        for (name, url, page) in zip(album_name_list, album_url_list, album_page_list):
            album = Album()
            album.name = name
            album.url = url
            album.page = str(page)[0: -1]
            album_list.append(album)
        try:
            a = driver1.find_element(By.XPATH, '//nav[@class="uk-container uk-padding-small m-pagination"]/ul[@class="uk-pagination uk-flex-center uk-margin-remove uk-visible@s"]/li[last()]/a/span').text
        except:
            a = '没有下一页'
        while a == '下一页':
            print('----------点击下一页-------------')
            time.sleep(1)
            driver1.find_element(By.XPATH, '//nav[@class="uk-container uk-padding-small m-pagination"]/ul[@class="uk-pagination uk-flex-center uk-margin-remove uk-visible@s"]/li[last()]/a/span').click()
            current_url = url_request(driver1.current_url)
            album_name_list = current_url.xpath('//h2[@class="uk-card-title uk-margin-small-top uk-margin-remove-bottom"]/a/text()').getall()
            album_url_list = current_url.xpath('//h2[@class="uk-card-title uk-margin-small-top uk-margin-remove-bottom"]/a/@href').getall()
            album_page_list = current_url.xpath('//div[@class="uk-card-badge uk-label u-label"]/text()').getall()
            for (name, url, page) in zip(album_name_list, album_url_list, album_page_list):
                album = Album()
                album.name = name
                album.url = url
                album.page = str(page)[0: -1]
                album_list.append(album)
            try:
                a = driver1.find_element(By.XPATH, '//nav[@class="uk-container uk-padding-small m-pagination"]/ul[@class="uk-pagination uk-flex-center uk-margin-remove uk-visible@s"]/li[last()]/a/span').text
            except:
                break
        # ---------------------------------------获取相册对象 end------------------------------------------------
        for album in album_list:
            picture_name = 1 # 初始化picture_name
            rstr = r"[\/\\\:\*\?\"\<\>\|]"
            album.name = re.sub(rstr, "", album.name)
            path = os.path.join(path1, model.model_name, album.name)
            if os.path.exists(path):
                print("！！！！！文件夹存在，不创建，爬取此album ！！！！！！")
                continue
            if not os.path.exists(path):
                os.makedirs(path)
            print('----开始爬取此album中的图片----', album.name, album.page, album.url)
            driver1.get(album.url)
            time.sleep(2)
            while picture_name <= int(album.page):
                image_url = driver1.find_element(By.XPATH, '/html/body/section[1]/div/div/main/article/figure/img').get_attribute('src')
                t = threading.Thread(target=download_iamge, name='Thread-' + str(picture_name), args=[image_url, path, picture_name])
                t.start()
                t.join()
                # 每爬取一次，图片名称加一
                driver1.find_element(By.XPATH,'//div[@class="uk-position-center-right uk-overlay uk-overlay-default f-swich"]').click()
                time.sleep(random.randint(1, 2))
                picture_name = picture_name + 1
            # 随机睡眠
            time.sleep(random.randint(1, 5))
    driver1.close()
    driver1.quit()
 
 
 
 
 