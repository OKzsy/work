#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
# @Time    : 2024/08/24 09:28
# @Author  : zhaoss
# @FileName: filter_logger.py
# @Email   : zss@hnas.cn
Description:

Parameters

"""
import logging
from random import choice


def filter_maker():
    """
    This is a filter which injects contextual information into the log.

    Rather than use actual contextual information, we just use random
    data in this demo.
    """

    def filter(record):
        USERS = ["jim", "fred", "sheila"]
        IPS = ["123.231.231.123", "127.0.0.1", "192.168.0.1"]
        level = getattr(logging, "WARNING")
        if record.levelno < level:
            record.ip = choice(IPS)
            record.user = choice(USERS)
            return True

    return filter


if __name__ == "__main__":
    levels = (
        logging.DEBUG,
        logging.INFO,
        logging.WARNING,
        logging.ERROR,
        logging.CRITICAL,
    )
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)-15s %(name)-5s %(levelname)-8s IP: %(ip)-15s User: %(user)-8s %(message)s",
    )
    a1 = logging.getLogger("a.b.c")
    a2 = logging.getLogger("d.e.f")

    a1.addFilter(filter_maker())
    a2.addFilter(filter_maker())
    a1.debug("A debug message")
    a1.info("An info message with %s", "some parameters")
    for x in range(10):
        lvl = choice(levels)
        lvlname = logging.getLevelName(lvl)
        a2.log(lvl, "A message at %s level with %d %s", lvlname, 2, "parameters")
