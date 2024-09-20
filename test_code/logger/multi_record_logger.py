#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2024/08/23 21:29
# @Author  : zhaoss
# @FileName: multi_record_logger.py
# @Email   : zss@hnas.cn
Description:
日志记录要求：
1、把 DEBUG 以上级别的日志信息写于文件，
2、把 INFO 以上的日志信息输出到控制台。
3、再假设日志文件需要包含时间戳
4、控制台信息则不需要
5、在程序的不同模块中将日志记录到一个文件
Parameters

"""
import os
import time
import logging


def main():
    # 配置一个根记录器, 配置文件处理器和控制台处理器, 文件处理器设置带时间戳的formatter, 控制台处理器不需要
    root_logger = logging.getLogger("root")
    # 注意处理根记录器的默认级别, 默认级别为logging.warning
    root_logger.setLevel(logging.DEBUG)
    # 创建一个文件处理器, 并设置级别为debug
    fh = logging.FileHandler("multi_spam.log", mode="w")
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s %(name)-12s %(levelname)-8s %(message)s", datefmt="%m-%d %H:%M"
    )
    fh.setFormatter(formatter)
    # 创建控制台处理器，并设置级别为debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter("%(name)-12s: %(levelname)-8s %(message)s")
    ch.setFormatter(formatter)
    root_logger.addHandler(fh)
    root_logger.addHandler(ch)
    # 创建日志消息
    root_logger.info("Jackdaws love my big sphinx of quartz.")
    # 模拟不同模块的日志
    logger1 = logging.getLogger("root.logger1")
    logger2 = logging.getLogger("root.logger2")
    # 创建日志消息
    logger1.debug("Quick zephyrs blow, vexing daft Jim.")
    logger1.info("How quickly daft jumping zebras vex.")
    logger2.warning("Jail zesty vixen who grabbed pay from quack.")
    logger2.error("The five boxing wizards jump quickly.")

    return None


if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    print("time: %.4f secs." % (end_time - start_time))
