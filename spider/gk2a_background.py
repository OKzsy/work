#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2021/3/24 16:04
# @Author  : zhaoss
# @FileName: gk2a_background.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
经过定制化修改，下载韩国gk2a卫星影像，自动更新电脑背景

Parameters


"""

import os
import datetime
import requests
import logging
from logging.handlers import TimedRotatingFileHandler
import win32api, win32con, win32gui

root_path = r"D:\back_pic\gk2a"
headers = {
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Connection": "keep-alive",
    "Host": "nmsc.kma.go.kr",
    "Referer": "http://nmsc.kma.go.kr/enhome/html/satellite/viewer/selectGk2aSatViewer.do?view=basic",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36"
}


def set_log(logfile=os.path.join(root_path, 'log.txt')):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    # fh = logging.FileHandler(logfile, mode='a')
    fh = TimedRotatingFileHandler(logfile, when='D', interval=1, backupCount=1)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger


class gk2awalls(object):
    """
    rule of basic images:

    full disk:
        RGB TRUE:
            https://nmsc.kma.go.kr/IMG/GK2A/AMI/PRIMARY/L1B/COMPLETE/FD/202010/30/06/gk2a_ami_le1b_rgb-true_fd010ge_202010300610.srv.png
        enhanced IR 10.5um:
            https://nmsc.kma.go.kr/IMG/GK2A/AMI/PRIMARY/L1B/COMPLETE/FD/202010/30/06/gk2a_ami_le1b_enhc-color-ir105_fd020ge_202010300640.srv.png

    East Asia:
        RGB TRUE:
        RGB NATURAL
        RGB DAYNIGHT:
            https://nmsc.kma.go.kr/IMG/GK2A/AMI/PRIMARY/L1B/COMPLETE/EA/202011/02/07/gk2a_ami_le1b_rgb-daynight_ea020lc_202011020740.srv.png
    """

    def __init__(self, time_utc, gk2a_type):
        self.time_utc = time_utc
        self.type = gk2a_type  # 'enhc-color-ir105_fd020ge'
        self.status = False
        self.remote_path = 'https://nmsc.kma.go.kr/IMG/GK2A/AMI/PRIMARY/L1B/COMPLETE/EA/' + \
                           self.time_utc.strftime('%Y%m') + '/' + self.time_utc.strftime(
            '%d') + '/' + self.time_utc.strftime('%H') + '/' + \
                           'gk2a_ami_le1b_{}_{}.srv.png'.format(self.type, self.time_utc.strftime('%Y%m%d%H%M'))
        self.local_path = os.path.join(root_path, 'images',
                                       self.time_utc.strftime('%Y%m'), self.time_utc.strftime('%d'),
                                       self.time_utc.strftime('%H'),
                                       'gk2a_ami_le1b_{}_{}.srv.png'.format(self.type,
                                                                            self.time_utc.strftime('%Y%m%d%H%M')))

        self._check_is_get()
        if os.path.exists(self.local_path) and os.path.getsize(self.local_path) > 10000:
            self.status = True
            self._set_wallpaper()

    def _check_is_get(self):
        re = requests.get(self.remote_path, headers=headers)
        info = re.headers
        if info.get('Content-Type') == 'image/png':
            logger.info(f'remote found {self.remote_path}')
            if os.path.exists(self.local_path):
                if float(info.get("Content-length")) == os.path.getsize(self.local_path):
                    logger.info(f'Already downloaded of {self.local_path}')
                else:
                    self._get_png(re.content, self.local_path)
            else:
                self._get_png(re.content, self.local_path)
        else:
            logger.warning(f'not found {self.remote_path}')

    @staticmethod
    def _get_png(data, local_path):
        if not os.path.exists(os.path.dirname(local_path)): os.makedirs(os.path.dirname(local_path))
        with open(local_path, 'wb') as f:
            f.write(data)
            logger.info(f'Download Success of {local_path}')
        return

    def _set_wallpaper(self, loc=6):
        logger.info(f'begin Set {self.local_path}')
        # 打开指定注册表路径
        key = win32api.RegOpenKeyEx(win32con.HKEY_CURRENT_USER, "Control Panel\\Desktop", 0, win32con.KEY_SET_VALUE)
        # 最后的参数:2拉伸,0居中,6适应,10填充,0平铺
        win32api.RegSetValueEx(key, "WallpaperStyle", 0, win32con.REG_SZ, "2")
        # 最后的参数:1表示平铺,拉伸居中等都是0
        win32api.RegSetValueEx(key, "TileWallpaper", 0, win32con.REG_SZ, "0")
        # 刷新桌面
        logger.info(f'begin Set {self.local_path}')
        # win32gui.SystemParametersInfo(win32con.SPI_SETDESKWALLPAPER, self.local_path, win32con.SPIF_SENDWININICHANGE)
        win32gui.SystemParametersInfo(win32con.SPI_SETDESKWALLPAPER, self.local_path, 1 + 2)
        logger.info(f'close Set {self.local_path}')
        logger.info(f'Set {self.local_path}')
        return


if __name__ == "__main__":
    '''
    This code set GK2A satellite basic image as wallpaper
    '''
    logger = set_log()

    # enhance IR 10.5
    gk2a_type = 'rgb-daynight_ea020lc'
    init_minute = 10
    end = True
    while end:
        utc_today = datetime.datetime.utcnow() - datetime.timedelta(minutes=init_minute)  # 获取GMT时间并减去10分钟
        delat_utc_today = utc_today.strftime("%Y/%m/%d/%H/%M")  # 时间格式化
        # 分钟向下取整
        delat_utc_today_list = list(delat_utc_today)
        delat_utc_today_list[-1] = "0"
        time_r = datetime.datetime.strptime(''.join(delat_utc_today_list), "%Y/%m/%d/%H/%M")
        if float(time_r.strftime('%H')) >= 0 and float(time_r.strftime('%H')) <= 9:
            gk2a_type = 'rgb-true_ea010lc'
        else:
            gk2a_type = 'enhc-color-wv073_ea020lc'
        gk2a_d = gk2awalls(time_r, gk2a_type)
        if gk2a_d.status:
            end = False
        else:
            init_minute += 10
