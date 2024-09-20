#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2024/05/02 08:19
# @Author  : zhaoss
# @FileName: check_notification.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:

Parameters

"""
import os
import sys
import time
import pickle
import requests
from bs4 import BeautifulSoup
import lxml
import urllib.parse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.182 Safari/537.36",
}


class AUTO_EMAIL:
    """用于发送email的类"""

    def __init__(self) -> None:
        self.__my_email = "AIRIoffice@163.com"
        self.__password = "TIZNNGESLAAMIYEQ"
        self.__my_email_port = 465
        self.__my_email_server = "smtp.163.com"
        pass

    # 生成信息
    def __generate_message(self, email_address, web=None, text=None, link=None):
        # 创建一个多类型内容的封装器
        msg = MIMEMultipart("alternative")
        # 主题
        msg["Subject"] = "自动跟踪到了网站内容变化"
        # 发送邮箱
        msg["From"] = self.__my_email
        # 接收邮箱
        msg["To"] = email_address
        # 创建不同类型邮件内容（文本，图片，附件）
        # 创建html类型邮件
        html_begin = """\
                        <html>
                            <body>
                     """
        html = html_begin
        num = len(web)
        if num > 0:
            for i in range(num):
                html = (
                    html
                    + """<p>{web_name}有更新，链接如下：</p>""".format(web_name=web[i])
                    + "\n"
                )
                html = (
                    html
                    + """<p><a href="{link}">{title}</a></p>""".format(
                        link=link[i], title=text[i]
                    )
                    + "\n"
                )
        html_end = """\
                            <body>
                        <html>
                     """
        html = html + html_end
        # 创建一个MIMEText对象，用于包含HTML格式的邮件正文
        part2 = MIMEText(html, "html", "utf-8")
        # 将MIMEText对象添加到MIMEMultipart对象中
        msg.attach(part2)
        message = msg.as_string()
        del msg
        return message

    # 发送定制email
    def send_email(self, email_adress, web=None, text=None, link=None):
        # 创建email服务器连接
        with smtplib.SMTP_SSL(self.__my_email_server, self.__my_email_port) as server:
            # 登录email服务器
            server.login(self.__my_email, self.__password)
            # 发送email
            message = self.__generate_message(
                email_adress, web=web, text=text, link=link
            )
            server.sendmail(self.__my_email, email_adress, message)
        pass


def geturl(url):
    i = 0
    while i < 3:
        try:
            html = requests.get(url, headers=headers, timeout=30)
            html.encoding = "utf-8"
            return html.text
        except requests.exceptions.RequestException as e:
            time.sleep(5.0)
            i += 1


def parse_page_hgd(url):
    html = geturl(url)
    # 解析内容
    bsobj = BeautifulSoup(html, "lxml")
    doctor_node = bsobj.find("div", {"class": "menu-bottom menu-list"})
    news_node = doctor_node.find("li", {"class": "news n1 clearfix"})
    title_node = news_node.find("div", {"class": "news_title"})
    href = title_node.a["href"]
    href = urllib.parse.urljoin(url, href)
    title = title_node.a["title"]
    return href, title


def parse_page_kxy(url):
    html = geturl(url)
    # 解析内容
    bsobj = BeautifulSoup(html, "lxml")
    news_node = bsobj.find("div", {"class": "txtslist"})
    title_node = news_node.find("li")
    href = title_node.a["href"]
    href = urllib.parse.urljoin(url, href)
    title = title_node.a["title"]
    return href, title


def parse_page_hndx(url):
    html = geturl(url)
    # 解析内容
    bsobj = BeautifulSoup(html, "lxml")
    news_node = bsobj.find("div", {"class": "nkzl-news-box"})
    title_node = news_node.find("li", {"id": "line_u6_0"})
    href = title_node.a["href"]
    href = urllib.parse.urljoin(url, href)
    title = title_node.a.p.text
    return href, title


def main():
    # 获取程序运行路径
    currentpath = os.path.split(os.path.realpath(__file__))[0]
    # 存储原始信息到文件
    ori_mess_filepath = os.path.join(currentpath, "web.pkl")
    if not os.path.exists(ori_mess_filepath):
        # 创建空信息
        mess = {
            "哈工大网站": {
                "base_link": "https://yzb.hit.edu.cn/8824/list.htm",
                "link": "",
                "title": "",
                "flag": 0,
            },
            "研究生工作部网站": {
                "base_link": "https://www.hnskxy.com/yjsgz/index/tzgg.htm",
                "link": "",
                "title": "",
                "flag": 1,
            },
            "河南大学网站": {
                "base_link": "https://cep.henu.edu.cn/zsjy/bsyjszs.htm",
                "link": "",
                "title": "",
                "flag": 2,
            },
        }
        # 写入文件
        with open(ori_mess_filepath, "wb") as fj:
            pickle.dump(mess, fj)
    else:
        # 读取信息
        with open(ori_mess_filepath, "rb") as fj:
            mess = pickle.load(fj)
    # 解析网页
    update_count = 0
    update_web = []
    update_text = []
    update_link = []
    for key, value in mess.items():
        url = value["base_link"]
        text = value["title"]
        flag = value["flag"]
        if flag == 0:
            newlink, newtitle = parse_page_hgd(url=url)
            if text != newtitle:
                mess[key]["link"] = newlink
                mess[key]["title"] = newtitle
                update_web.append(key)
                update_text.append(newtitle)
                update_link.append(newlink)
                update_count += 1
        elif flag == 1:
            newlink, newtitle = parse_page_kxy(url=url)
            if text != newtitle:
                mess[key]["link"] = newlink
                mess[key]["title"] = newtitle
                update_web.append(key)
                update_text.append(newtitle)
                update_link.append(newlink)
                update_count += 1
        elif flag == 2:
            newlink, newtitle = parse_page_hndx(url=url)
            if text != newtitle:
                mess[key]["link"] = newlink
                mess[key]["title"] = newtitle
                update_web.append(key)
                update_text.append(newtitle)
                update_link.append(newlink)
                update_count += 1
    # 如果有更新，更新文件，并发送更新邮件
    if update_count > 0:
        # 更新文件
        with open(ori_mess_filepath, "wb") as fj:
            pickle.dump(mess, fj)
        # 发送邮件
        autoemail = AUTO_EMAIL()
        autoemail.send_email(
            "hpu_zss@163.com",
            update_web,
            update_text,
            update_link,
        )

    return None


if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
