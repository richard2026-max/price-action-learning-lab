"""合成数据生成器测试：确定性、OHLC 有效性、交易日常量。"""

from datetime import date

from app.domain.bar import SessionType
from app.domain.instrument import SPY_SYNTH
from app.services.calendar import XNYSCalendar
from app.services.synthetic import generate_day_1m, generate_range_1m


def test_deterministic_same_seed_same_bars():
    cal = XNYSCalendar()
    a, pa = generate_day_1m(SPY_SYNTH, date(2024, 6, 3), cal, global_seed=42)
    b, pb = generate_day_1m(SPY_SYNTH, date(2024, 6, 3), cal, global_seed=42)
    assert a == b and pa == pb
    c, _ = generate_day_1m(SPY_SYNTH, date(2024, 6, 3), cal, global_seed=43)
    assert a != c


def test_no_bars_on_holiday_or_weekend():
    cal = XNYSCalendar()
    assert generate_day_1m(SPY_SYNTH, date(2024, 12, 25), cal, 42)[0] == []
    assert generate_day_1m(SPY_SYNTH, date(2024, 6, 1), cal, 42)[0] == []  # 周六


def test_bar_counts_and_validity():
    cal = XNYSCalendar()
    # 常规日：premarket 330 + RTH 390 = 720 根 1m
    bars, _ = generate_day_1m(SPY_SYNTH, date(2024, 6, 3), cal, 42)
    assert len(bars) == 720
    assert sum(1 for b in bars if b.session == SessionType.RTH) == 390
    assert sum(1 for b in bars if b.session == SessionType.PREMARKET) == 330
    for b in bars:
        assert b.low <= b.open <= b.high
        assert b.low <= b.close <= b.high
        assert b.volume >= 0
    # 半日市：RTH 210 根
    bars2, _ = generate_day_1m(SPY_SYNTH, date(2024, 7, 3), cal, 42)
    assert sum(1 for b in bars2 if b.session == SessionType.RTH) == 210


def test_range_continuity_across_days():
    cal = XNYSCalendar()
    bars = generate_range_1m(SPY_SYNTH, date(2024, 6, 3), date(2024, 6, 7), cal, 42)
    days = sorted({b.ts_open_utc.date() for b in bars})
    assert days == [date(2024, 6, 3), date(2024, 6, 4), date(2024, 6, 5), date(2024, 6, 6), date(2024, 6, 7)]
