#!/usr/bin/env/ python3
# -*- coding:utf-8 -*-
import time
import os
import contextlib
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def main(url):
    chrome_options = Options()
    # chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('log-level=3')
    chrome_options.add_argument(r'--user-data-dir=C:\Users\01\AppData\Local\Google\Chrome\User Data\Default')
    # 获取浏览器驱动
    driver = webdriver.Chrome(chrome_options=chrome_options)
    driver.maximize_window()
    driver.get(url)
    # 登录账号
    if driver.find_element_by_xpath('//*[@id="top-index-loginUrl"]').text:
        element_login = driver.find_element_by_xpath('// *[ @ id = "top-index-loginUrl"]')
        element_login.click()
        username = '15239194035'
        passwd = '120503xz'
        time.sleep(1)
        element_username = driver.find_element_by_xpath(
            '/html/body/div[1]/div[3]/div/div/div[1]/div[3]/span[3]/div[1]/span/form/div[2]/div/div/div/input')
        element_username.send_keys(username)
        element_pwd = driver.find_element_by_xpath(
            '/html/body/div[1]/div[3]/div/div/div[1]/div[3]/span[3]/div[1]/span/form/div[3]/div/div/div/input')
        element_pwd.send_keys(passwd)
        # 单击回车键
        element_pwd.send_keys(Keys.ENTER)
    # 判断是否有弹窗弹出
    if EC.alert_is_present()(driver):
        pass
    # 等待页加载，并切换到需要购买的产品页面等待抢购
    page_wait = WebDriverWait(driver, 10)
    # element_pro_list = page_wait.until(lambda d: d.find_element_by_xpath('//*[@id="pro-list"]/li[8]/div/a'))
    element_pro_list = page_wait.until(lambda d: d.find_element_by_xpath('//*[@id="pro-list"]/li[1]'))
    element_pro_list.click()
    # 设置等待
    wait = WebDriverWait(driver, 10)
    # 存储原始窗口的 ID
    original_window = driver.current_window_handle
    # 等待新窗口或标签页
    wait.until(EC.number_of_windows_to_be(2))
    # 循环执行，直到找到一个新的窗口句柄
    for window_handle in driver.window_handles:
        if window_handle != original_window:
            driver.switch_to.window(window_handle)
            break

    # 等待商品可以抢购，并抢购
    # 设置等待
    def buyisable(drv):
        element_product = drv.find_element_by_xpath('//*[@id="pro-operation"]/*[contains(@class,"product-button02")]')
        if 'disabled' in element_product.get_attribute('class'):
            print('check')
            return False
        else:
            return element_product

    try:
        buy_active = True
        while buy_active:
            buy_wait = WebDriverWait(driver, timeout=10, poll_frequency=0.5)
            element_buy = buy_wait.until(lambda d: buyisable(d))
            print(element_buy.text)
            element_buy.click()
            try:
                ele_frame = WebDriverWait(driver, 2).until(lambda d: d.find_element_by_css_selector('#queueIframe'))
            except:
                buy_active = False
                break
            else:
                driver.switch_to.frame(ele_frame)
                active = True
                while active:
                    queue_ele = driver.find_element_by_css_selector('body > div.queue-tips')
                    print(queue_ele.text)
                    if '排队中' not in queue_ele.text:
                        driver.find_element_by_css_selector('body > div.queue-btn').click()
                        driver.switch_to.default_content()
                        active = False
    except Exception as e:
        print(e)
        driver.quit()
    os.system('pause')

import requests
from requests import exceptions
import os

# resq = requests.get("https://www.baidu.com")
# # 查看相应类型
# print(type(resq))
# # 输出状态吗
# print(resq.status_code)
# # 输出相应类型 text
# print(type(resq.text))
# # 输出相应内容
# print(resq.text.encode("utf-8"))
# # 输出cookies
# print(resq.cookies)
# get 请求
# resq = requests.get('http://httpbin.org/get')
# print(resq.text)
# # 带参数请求
# resq = requests.get("http://httpbin.org/get?name=jyx&age=18")
# print(resq.text)
# # 封装参数请求
# param = {"name": 'zss',
#         "age": "19"}
# resq = requests.get('http://httpbin.org/get', params=param)
# print(type(resq.text))
# print(resq.json())
# resq = requests.get("http://github.com/favicon.ico")
# print(type(resq.text), type(resq.content))
# # 输出相应内容
# print(resq.text)
# # 输出相应二进制内容
# dir_path = r"e:\PythonCode\pic"
# ico = os.path.join(dir_path,'favicon.ico')
# with open(ico, 'wb') as f:
#     f.write(resq.content)
# f.close
headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36"}
# resq = requests.get("https://www.zhihu.com/explore", headers=headers)
# print(resq.text)
# 使用post
data = {'name':"zss", "age":"20"}
resp = requests.post('http://httpbin.org/post', data=data, headers=headers)
print(resp.text)