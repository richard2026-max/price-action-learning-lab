"""交易日历测试：RTH、盘前、半日市、节假日、DST。"""

from datetime import UTC, date, datetime

from app.services.calendar import XNYSCalendar


def test_holiday_not_trading_day():
    cal = XNYSCalendar()
    assert not cal.is_trading_day(date(2024, 12, 25))  # 圣诞
    assert not cal.is_trading_day(date(2024, 1, 15))  # MLK
    assert not cal.is_trading_day(date(2024, 11, 28))  # 感恩节
    assert not cal.is_trading_day(date(2024, 7, 4))  # 独立日
    assert cal.is_trading_day(date(2024, 1, 2))


def test_early_close_half_day():
    cal = XNYSCalendar()
    assert cal.is_early_close(date(2024, 7, 3))  # 独立日前半日市
    assert cal.is_early_close(date(2024, 11, 29))  # 感恩节次日
    assert cal.is_early_close(date(2024, 12, 24))
    assert not cal.is_early_close(date(2024, 7, 5))


def test_rth_window_regular_and_half_day():
    cal = XNYSCalendar()
    # 常规日：09:30-16:00 ET = 390 分钟
    w = {s.session_type: s for s in cal.sessions_for(date(2024, 6, 3))}
    assert (w["rth"].end_utc - w["rth"].start_utc).total_seconds() == 390 * 60
    assert w["rth"].start_utc == datetime(2024, 6, 3, 13, 30, tzinfo=UTC)
    # 盘前 04:00-09:30
    assert (w["premarket"].end_utc - w["premarket"].start_utc).total_seconds() == 330 * 60
    # 半日市：09:30-13:00 = 210 分钟
    w2 = {s.session_type: s for s in cal.sessions_for(date(2024, 7, 3))}
    assert (w2["rth"].end_utc - w2["rth"].start_utc).total_seconds() == 210 * 60


def test_dst_summer_and_winter_utc_offsets():
    cal = XNYSCalendar()
    # 冬令时（EDT 结束后）：09:30 ET = 14:30 UTC
    w = {s.session_type: s for s in cal.sessions_for(date(2024, 12, 2))}
    assert w["rth"].start_utc.hour == 14
    # 夏令时：09:30 ET = 13:30 UTC
    w2 = {s.session_type: s for s in cal.sessions_for(date(2024, 7, 10))}
    assert w2["rth"].start_utc.hour == 13


def test_prev_next_trading_day():
    cal = XNYSCalendar()
    assert cal.prev_trading_day(date(2024, 1, 2)) == date(2023, 12, 29)
    assert cal.next_trading_day(date(2023, 12, 29)) == date(2024, 1, 2)
