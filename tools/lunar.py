"""农历转换工具 — 使用查表法 (1900-2100)"""

# 农历数据: 每个元素16位，低4位闰月月份(0=无闰月)，高12位每月大小月(1=大月30天,0=小月29天)
LUNAR_INFO = [
    0x04bd8, 0x04ae0, 0x0a570, 0x054d5, 0x0d260, 0x0d950, 0x16554, 0x056a0, 0x09ad0, 0x055d2,
    0x04ae0, 0x0a5b6, 0x0a4d0, 0x0d250, 0x1d255, 0x0b540, 0x0d6a0, 0x0ada2, 0x095b0, 0x14977,
    0x04970, 0x0a4b0, 0x0b4b5, 0x06a50, 0x06d40, 0x1ab54, 0x02b60, 0x09570, 0x052f2, 0x04970,
    0x06566, 0x0d4a0, 0x0ea50, 0x06e95, 0x05ad0, 0x02b60, 0x186e3, 0x092e0, 0x1c8d7, 0x0c950,
    0x0d4a0, 0x1d8a6, 0x0b550, 0x056a0, 0x1a5b4, 0x025d0, 0x092d0, 0x0d2b2, 0x0a950, 0x0b557,
    0x06ca0, 0x0b550, 0x15355, 0x04da0, 0x0a5b0, 0x14573, 0x052b0, 0x0a9a8, 0x0e950, 0x06aa0,
    0x0aea6, 0x0ab50, 0x04b60, 0x0aae4, 0x0a570, 0x05260, 0x0f263, 0x0d950, 0x05b57, 0x056a0,
    0x096d0, 0x04dd5, 0x04ad0, 0x0a4d0, 0x0d4d4, 0x0d250, 0x0d558, 0x0b540, 0x0b6a0, 0x195a6,
    0x095b0, 0x049b0, 0x0a974, 0x0a4b0, 0x0b27a, 0x06a50, 0x06d40, 0x0af46, 0x0ab60, 0x09570,
    0x04af5, 0x04970, 0x064b0, 0x074a3, 0x0ea50, 0x06b58, 0x05ac0, 0x0ab60, 0x096d5, 0x092e0,
    0x0c960, 0x0d954, 0x0d4a0, 0x0da50, 0x07552, 0x056a0, 0x0abb7, 0x025d0, 0x092d0, 0x0cab5,
    0x0a950, 0x0b4a0, 0x0baa4, 0x0ad50, 0x055d9, 0x04ba0, 0x0a5b0, 0x15176, 0x052b0, 0x0a930,
    0x07954, 0x06aa0, 0x0ad50, 0x05b52, 0x04b60, 0x0a6e6, 0x0a4e0, 0x0d260, 0x0ea65, 0x0d530,
    0x05aa0, 0x076a3, 0x096d0, 0x04afb, 0x04ad0, 0x0a4d0, 0x1d0b6, 0x0d250, 0x0d520, 0x0dd45,
    0x0b5a0, 0x056d0, 0x055b2, 0x049b0, 0x0a577, 0x0a4b0, 0x0aa50, 0x1b255, 0x06d20, 0x0ada0,
    0x14b63, 0x09370, 0x049f8, 0x04970, 0x064b0, 0x168a6, 0x0ea50, 0x06aa0, 0x1a6c4, 0x0aae0,
    0x092e0, 0x0d2e3, 0x0c960, 0x0d557, 0x0d4a0, 0x0da50, 0x05d55, 0x056a0, 0x0a6d0, 0x055d4,
    0x052d0, 0x0a9b8, 0x0a950, 0x0b4a0, 0x0b6a6, 0x0ad50, 0x055a0, 0x0aba4, 0x0a5b0, 0x052b0,
    0x0b273, 0x06930, 0x07337, 0x06aa0, 0x0ad50, 0x14b55, 0x04b60, 0x0a570, 0x054e4, 0x0d160,
    0x0e968, 0x0d520, 0x0daa0, 0x16aa6, 0x056d0, 0x04ae0, 0x0a9d4, 0x0a4d0, 0x0d150, 0x0f252,
    0x0d520,
]

# 天干地支
TIAN_GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
DI_ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
SHENG_XIAO = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]
LUNAR_MONTH = ["正", "二", "三", "四", "五", "六", "七", "八", "九", "十", "冬", "腊"]
LUNAR_DAY = [
    "初一", "初二", "初三", "初四", "初五", "初六", "初七", "初八", "初九", "初十",
    "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
    "廿一", "廿二", "廿三", "廿四", "廿五", "廿六", "廿七", "廿八", "廿九", "三十",
]


class LunarCalendar:
    """公历转农历"""

    @staticmethod
    def _days_in_year(year):
        """返回农历年总天数"""
        info = LUNAR_INFO[year - 1900]
        days = 0
        for i in range(12):
            days += 30 if (info >> (15 - i)) & 1 else 29
        leap = info & 0xf
        if leap:
            days += 30 if (info >> (15 - leap)) & 1 else 29
        return days

    @staticmethod
    def solar_to_lunar(solar_date):
        """
        solar_date: datetime.date
        return: (lunar_year, lunar_month, lunar_day, is_leap, year_str)
        """
        # 计算与1900-01-31(农历1900-01-01)的天数差
        base_date = __import__('datetime').date(1900, 1, 31)
        offset = (solar_date - base_date).days

        year = 1900
        while year <= 2100:
            days_in_year = LunarCalendar._days_in_year(year)
            if offset < days_in_year:
                break
            offset -= days_in_year
            year += 1

        info = LUNAR_INFO[year - 1900]
        leap = info & 0xf
        month = 1
        is_leap = False

        for m in range(1, 13):
            days_in_month = 30 if (info >> (16 - m)) & 1 else 29
            if offset < days_in_month:
                break
            offset -= days_in_month
            month = m + 1

        # 闰月处理
        if leap and month == leap + 1:
            days_in_leap = 30 if (info >> (16 - leap)) & 1 else 29
            if offset >= days_in_leap:
                offset -= days_in_leap
            else:
                is_leap = True
                month = leap

        day = offset + 1

        # 天干地支
        gan_idx = (year - 4) % 10
        zhi_idx = (year - 4) % 12
        year_str = f"{TIAN_GAN[gan_idx]}{DI_ZHI[zhi_idx]}年({SHENG_XIAO[zhi_idx]})"

        return year, month, day, is_leap, year_str

    @staticmethod
    def format_lunar_date(solar_date):
        """返回格式化农历日期字符串"""
        try:
            y, m, d, leap, year_str = LunarCalendar.solar_to_lunar(solar_date)
            month_str = ("闰" if leap else "") + LUNAR_MONTH[m - 1] + "月"
            day_str = LUNAR_DAY[d - 1]
            return f"{year_str} {month_str}{day_str}"
        except Exception:
            return ""
