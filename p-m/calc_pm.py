import os
import math


def air_press(altitu):
    """用于计算给定海拔高度的气压,并同时返回湿度计常数"""
    press = 101.3 * ((293 - 0.0065 * altitu) / 293) ** 5.26
    const_hygrometer = 0.665 * 10 ** (-3) * press
    return round(press, 1), round(const_hygrometer, 3)


def sat_vapour_pressure(temperature_tuple):
    """使用最高温度和最低温度计算平均饱和水汽压,和饱和水汽压曲线斜率"""
    temp_max, temp_min = temperature_tuple
    temp_mean = (temp_max + temp_min) / 2
    svp_max = 0.6108 * math.exp(17.27 * temp_max / (temp_max + 237.3))
    svp_min = 0.6108 * math.exp(17.27 * temp_min / (temp_min + 237.3))
    svp = (svp_max + svp_min) / 2
    svp_mean = 0.6108 * math.exp(17.27 * temp_mean / (temp_mean + 237.3))
    slope = 4098 * svp_mean / (temp_mean + 237.3) ** 2
    return round(svp, 2), round(slope, 3)


def act_vapour_pressure(temperature_tuple, humidity_tuple):
    """利用温度和相对湿度数据计算实际水汽压"""
    temp_max, temp_min = temperature_tuple
    rh_max, rh_min = humidity_tuple
    svp_max = 0.6108 * math.exp(17.27 * temp_max / (temp_max + 237.3))
    svp_min = 0.6108 * math.exp(17.27 * temp_min / (temp_min + 237.3))
    avp = (svp_min * rh_max / 100 + svp_max * rh_min / 100) / 2
    return round(avp, 3)


svp = sat_vapour_pressure((25, 18))
avp = act_vapour_pressure((25, 18), (82, 54))
res = svp[0] - avp
print(res)
