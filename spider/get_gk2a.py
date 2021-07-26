#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2021/3/23 10:31
# @Author  : zhaoss
# @FileName: get_gk2a.py
# @Email   : zhaoshaoshuai@hnnydsj.com
Description:
下载韩国卫星gk2a影像，自动更换电脑背景

Parameters


"""

import os
import time
from datetime import datetime, timedelta
import urllib.request
import logging
import win32api, win32con, win32gui

root_path = f'{os.path.dirname(os.path.realpath(__file__))}'


def set_log(logfile=os.path.join(root_path, 'log.txt')):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(logfile, mode='a')

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger


def ceil_dt(dt, delta):
    return dt + (datetime.min - dt) % delta


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
        with urllib.request.urlopen(self.remote_path) as res:
            info = res.info()
            if info.get('Content-Type') == 'image/png':
                logger.info(f'remote found {self.remote_path}')
                if os.path.exists(self.local_path):
                    if float(info.get("Content-length")) == os.path.getsize(self.local_path):
                        logger.info(f'Already downloaded of {self.local_path}')
                    else:
                        self._get_png(res.read(), self.local_path)
                else:
                    self._get_png(res.read(), self.local_path)
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
        key = win32api.RegOpenKeyEx(win32con.HKEY_CURRENT_USER, "Control Panel\\Desktop", 0, win32con.KEY_SET_VALUE)
        win32api.RegSetValueEx(key, "WallpaperStyle", 6, win32con.REG_SZ, "6")
        win32api.RegSetValueEx(key, "TileWallpaper", 0, win32con.REG_SZ, "0")
        win32gui.SystemParametersInfo(win32con.SPI_SETDESKWALLPAPER, self.local_path, win32con.SPIF_SENDWININICHANGE)
        logger.info(f'Set {self.local_path}')
        return


if __name__ == "__main__":
    '''
    This code set GK2A satellite basic image as wallpaper
    '''
    logger = set_log()

    # enhance IR 10.5
    gk2a_type = 'rgb-daynight_ea020lc'
    while True:
        time_now = datetime.utcnow()
        time_now = ceil_dt(time_now, timedelta(minutes=10))
        # check 1hour ago
        for imn in range(0, 60, 10):
            time_r = time_now - timedelta(minutes=imn)
            if float(time_r.strftime('%H')) >= 0 and float(time_r.strftime('%H')) <= 7:
                gk2a_type = 'rgb-true_ea010lc'
            else:
                gk2a_type = 'enhc-color-ir105_ea020lc'
            gk2a_d = gk2awalls(time_r, gk2a_type)
            if gk2a_d.status: break

        time.sleep(60 * 5)  # sleep 5 minutes
