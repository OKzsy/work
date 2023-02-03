"""彭曼-蒙特斯计算"""
import os
import math
from datetime import date, time, timedelta


class ET0:
    """定义计算参照腾发量et0的类"""

    def __init__(self, lon, lat, dt, temperature, humidity, altitu, wind, period=None, tzone=8):
        """
        参数描述：
        dt:日期
        temperature: tuple[tmax(float), tmin(float)]
        humidity: tuple[hmax(int), hmin(int)]
        altitu: 单位是米(m)
        period: tuple[start_time(string:'hour-minute'), end_time(string:'hour-minute')]
        """
        """初始类属性"""
        self._lon = lon
        self._lat = lat
        self._julday = None
        self._wind = wind
        self._year, self._month, self._day = map(int, dt.split('-'))
        self._t_max, self._t_min = temperature
        self._rh_max, self._rh_min = humidity
        self._altitu = altitu
        self._tzone = tzone
        self._press, self._const_hygrometer = self.__air_press()
        self._svp, self._slope, self._avp = self.__sat_vapour_pressure()
        if period:
            self._st, self._et = period
            self._day_ra = self.__sun_hour_radia()
        else:
            self._day_ra = self.__sun_day_radia()
        self._rn = self.__net_longwave_radia()
        self._wind2 = self.__wspeed2()

    def __air_press(self):
        """用于计算给定海拔高度的气压,并同时返回湿度计常数"""
        press = 101.3 * ((293 - 0.0065 * self._altitu) / 293) ** 5.26
        const_hygrometer = 0.665 * 10 ** (-3) * press
        return round(press, 1), round(const_hygrometer, 3)

    def __sat_vapour_pressure(self):
        """使用最高温度和最低温度计算平均饱和水汽压,和饱和水汽压曲线斜率, 实际水汽压"""
        temp_mean = (self._t_max + self._t_min) / 2
        # 日平均气温有待优化
        temp_mean = 29.3
        svp_max = 0.6108 * math.exp(17.27 * self._t_max / (self._t_max + 237.3))
        svp_min = 0.6108 * math.exp(17.27 * self._t_min / (self._t_min + 237.3))
        svp = (svp_max + svp_min) / 2
        svp_mean = 0.6108 * math.exp(17.27 * temp_mean / (temp_mean + 237.3))
        slope = 4098 * svp_mean / (temp_mean + 237.3) ** 2
        avp = (svp_min * self._rh_max / 100 + svp_max * self._rh_min / 100) / 2
        return round(svp, 3), round(slope, 3), round(avp, 3)

    def __sun_day_radia(self):
        """以天为单位计算太阳天顶辐射"""
        deg2rad = math.pi / 180
        lat_rad = self._lat * deg2rad
        # 计算julday
        d0 = date(self._year, 1, 1)
        d1 = date(self._year, self._month, self._day)
        self._julday = (d1 - d0).days + 1
        # 计算太阳偏角
        sigm_rad = (23.45 * deg2rad) * math.sin((360 * (self._julday - 81) / 365) * deg2rad)
        # 计算日落时角
        sunset_rad = math.acos(-math.tan(lat_rad) * math.tan(sigm_rad))
        # 计算日地距离的倒数
        d = 1 + 0.033 * math.cos(2 * math.pi * self._julday / 365)
        # 计算以天为单位的太阳辐射
        day_ra = 24 * 60 * 0.082 * d * (sunset_rad * math.sin(lat_rad) * math.sin(sigm_rad) +
                                        math.cos(lat_rad) * math.cos(sigm_rad) * math.sin(sunset_rad)) / math.pi
        return day_ra

    def __sun_hour_radia(self):
        """以小时或者更短时间为单位计算太阳天顶辐射"""
        deg2rad = math.pi / 180
        lat_rad = self._lat * deg2rad
        # 计算太阳偏角
        sigm_rad = (23.45 * deg2rad) * math.sin((360 * (self._julday - 81) / 365) * deg2rad)
        # 计算日落时角
        sunset_rad = math.acos(-math.tan(lat_rad) * math.tan(sigm_rad))
        # 计算待计算点和时区中心经度之差
        diff_lon = self._lon - 15 * self._tzone
        # 计算日照时间的季节修正
        # 计算日角b
        b = 360 * (self._julday - 81) / 365
        b_rad = b * deg2rad
        sun_seasonal_cor = 0.1645 * math.sin(2 * b_rad) - 0.1255 * math.cos(b_rad) - 0.025 * math.sin(b_rad)
        # 计算待计算时段的中心时刻
        st_h, st_m = map(int, self._st.split('-'))
        et_h, et_m = map(int, self._et.split('-'))
        decimal_st = st_h + st_m / 60
        decimal_et = et_h + et_m / 60
        center_time = (decimal_et + decimal_st) / 2
        diff_time = decimal_et - decimal_st
        w = math.pi * (center_time + 0.06667 * diff_lon + sun_seasonal_cor - 12) / 12
        w1 = w - math.pi * diff_time / 24
        w2 = w + math.pi * diff_time / 24
        diff_w = w2 - w1
        # 计算日地距离的倒数
        d = 1 + 0.033 * math.cos(2 * math.pi * self._julday / 365)
        # 计算待求时段内的天顶辐射
        hour_ra = 12 * 60 * 0.082 * d * (diff_w * math.sin(lat_rad) * math.sin(sigm_rad) +
                                         math.cos(lat_rad) * math.cos(sigm_rad) * (
                                                 math.sin(w2) - math.sin(w1))) / math.pi
        return hour_ra

    def __net_longwave_radia(self):
        """计算净长波辐射"""
        deg2rad = math.pi / 180
        lat_rad = self._lat * deg2rad
        # 计算太阳偏角
        sigm_rad = (23.45 * deg2rad) * math.sin((360 * (self._julday - 81) / 365) * deg2rad)
        # 计算日落时角
        sunset_rad = math.acos(-math.tan(lat_rad) * math.tan(sigm_rad))
        # 计算日照时长
        day_n = 24 * sunset_rad / math.pi
        # 计算太阳辐射Rs
        rs = 0.16 * self._day_ra * math.sqrt(self._t_max - self._t_min)
        # 计算晴空太阳辐射Rso
        # 下边的式子是在没有修正系数（as,bs)的情况下使用
        # rso = (0.75 + 2 * 10 ** (-5) * self._altitu) * self._day_ra
        # 下边的式子是在有修正系数的情况下使用
        if self._month >= 4 and self._month <= 9:
            a = 0.17
            b = 0.45
        else:
            a = 0.14
            b = 0.45
        rso = (a + b) * self._day_ra
        # 计算净太阳辐射Rns
        rns = (1 - 0.23) * rs
        # 计算净长波辐射Rnl
        rnl = 4.903 * 10 ** (-9) * (((self._t_max + 273.16) ** 4 + (self._t_min + 273.16) ** 4) / 2) * \
              (0.34 - 0.14 * math.sqrt(self._avp)) * (1.35 * rs / rso - 0.35)
        # 计算净辐射
        rn = rns - rnl
        return rn

    def __wspeed2(self):
        """用以将气象学中的风速转换为农学中2m高的风速"""
        u2 = self._wind * 4.87 / math.log(67.8 * 10 - 5.42)
        return round(u2, 3)

    def month_et(self, avt_month, avt_lmonth):
        """按照月尺度计算et0"""
        # 计算土壤热通量
        g = 0.14 * (avt_month - avt_lmonth)
        # 计算蒸散量
        t_mean = (self._t_max + self._t_min) / 2
        temp_var1 = 0.408 * self._slope * (self._rn - g)
        temp_var2 = self._const_hygrometer * 900 * self._wind2 * (self._svp - self._avp) / (t_mean + 273)
        temp_var3 = self._slope + self._const_hygrometer * (1 + 0.34 * self._wind2)
        et0 = (temp_var1 + temp_var2) / temp_var3
        return round(et0, 3)

    def ten_days_et(self):
        """按照10天尺度计算et0"""
        # 计算蒸散量
        t_mean = (self._t_max + self._t_min) / 2
        temp_var1 = 0.408 * self._slope * (self._rn - 0)
        temp_var2 = self._const_hygrometer * 900 * self._wind2 * (self._svp - self._avp) / (t_mean + 273)
        temp_var3 = self._slope + self._const_hygrometer * (1 + 0.34 * self._wind2)
        et0 = (temp_var1 + temp_var2) / temp_var3
        return round(et0, 2)


# svp = sat_vapour_pressure((25, 18))
# avp = act_vapour_pressure((25, 18), (82, 54))
# res = svp[0] - avp
# print(res)
# ra = sun_day_radia(-22.54, '2022-05-15')
# sun_hour_radia('06-03', '18-42', 114, 35, '2022-09-03')
# net_longwave_radia(-22.54, '2022-05-15', ra, 25.1, 19.1, 0, 2.1)
et = ET0(119.27, 32.48, '2010-07-20', (34.4, 26.2), (84, 66), 5.2, 2.5)
res = et.ten_days_et()
print('hello')
