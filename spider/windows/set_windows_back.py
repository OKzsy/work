#!/usr/bin/env python
# _*_ coding:utf-8 _*_
#
# @Version : 1.0
# @Time    : 2020/04/15
# @Author  : zhaoss
# @File    : set_windows_back
# @Description: 自动设置桌面壁纸
#
#
import win32api, win32con, win32gui
import get_H8
import os


def set_desktop_windows(imagepath):
    k = win32api.RegOpenKeyEx(win32con.HKEY_CURRENT_USER, "Control Panel\\Desktop", 0, win32con.KEY_SET_VALUE)
    win32api.RegSetValueEx(k, "WallpaperStyle", 0, win32con.REG_SZ, "2")  # 2拉伸适应桌面，0桌面居中
    win32api.RegSetValueEx(k, "TileWallpaper", 0, win32con.REG_SZ, "0")
    win32gui.SystemParametersInfo(win32con.SPI_SETDESKWALLPAPER, imagepath, 1 + 2)


if __name__ == '__main__':
    print("正在下载图片")
    try:
        new_img_name = get_H8.dl_main()
    except Exception as e:
        print(e)
    # 这里的路径必须为绝对路径
    wallpaper_path = "D:\\back_pic\\" + new_img_name
    set_desktop_windows(wallpaper_path)
    os.remove(wallpaper_path)
