"""1m→5m session-aware 聚合测试：锚点、DST、session 隔离、不完整桶、缺失不填充。"""

from datetime import UTC, date, datetime, timedelta

from app.domain.bar import Bar, SessionType, Timeframe
from app.services.aggregation import aggregate_day_1m_to_5m
from app.services.calendar import ET, XNYSCalendar

cal = XNYSCalendar()


def _mk_bar(ts_open: datetime, o: float, h: float, lo: float, c: float, v: float = 100.0,
            session: SessionType = SessionType.RTH) -> Bar:
    return Bar(
        instrument_id="SPY", timeframe=Timeframe.M1,
        ts_open_utc=ts_open, ts_close_utc=ts_open + timedelta(minutes=1),
        open=o, high=h, low=lo, close=c, volume=v, session=session,
        provider="synthetic", feed="synthetic-v1", data_version="t",
    )


def test_rth_anchor_0930_et_and_bucket_count():
    bars5 = aggregate_day_1m_to_5m(_full_day_1m(date(2024, 6, 3)), date(2024, 6, 3), cal)
    rth = [b for b in bars5 if b.session == SessionType.RTH]
    pre = [b for b in bars5 if b.session == SessionType.PREMARKET]
    assert len(rth) == 78  # 390/5
    assert len(pre) == 66  # 330/5
    # 首根 RTH 5m 锚定 09:30 ET（夏令时 = 13:30 UTC）
    assert rth[0].ts_open_utc == datetime(2024, 6, 3, 13, 30, tzinfo=UTC)
    assert rth[0].ts_open_utc.astimezone(ET).hour == 9
    assert rth[0].ts_open_utc.astimezone(ET).minute == 30
    # 末根
    assert rth[-1].ts_open_utc.astimezone(ET).hour == 15
    assert rth[-1].ts_open_utc.astimezone(ET).minute == 55


def test_dst_first_trading_day_after_transition():
    """DST 切换发生在周日凌晨（休市）；验证切换后首个交易日的锚点 UTC 偏移正确切换。"""
    # 2024-03-10（周日）春令；03-11（周一）起为 EDT：09:30 ET = 13:30 UTC
    bars5 = aggregate_day_1m_to_5m(_full_day_1m(date(2024, 3, 11)), date(2024, 3, 11), cal)
    rth = [b for b in bars5 if b.session == SessionType.RTH]
    assert len(rth) == 78
    assert rth[0].ts_open_utc == datetime(2024, 3, 11, 13, 30, tzinfo=UTC)
    # 2024-11-03（周日）秋令；11-04（周一）起为 EST：09:30 ET = 14:30 UTC
    bars5b = aggregate_day_1m_to_5m(_full_day_1m(date(2024, 11, 4)), date(2024, 11, 4), cal)
    rthb = [b for b in bars5b if b.session == SessionType.RTH]
    assert len(rthb) == 78
    assert rthb[0].ts_open_utc == datetime(2024, 11, 4, 14, 30, tzinfo=UTC)


def test_no_cross_session_bucket():
    bars5 = aggregate_day_1m_to_5m(_full_day_1m(date(2024, 6, 3)), date(2024, 6, 3), cal)
    for b in bars5:
        w = {s.session_type: s for s in cal.sessions_for(date(2024, 6, 3))}[b.session.value]
        assert w.start_utc <= b.ts_open_utc < w.end_utc


def test_ohlc_aggregation_and_volume_sum():
    day = date(2024, 6, 3)
    windows = {s.session_type: s for s in cal.sessions_for(day)}
    t0 = windows["rth"].start_utc
    bars = [
        _mk_bar(t0 + timedelta(minutes=i), o=i + 1, h=i + 2, lo=i, c=i + 1.5, v=10)
        for i in range(5)
    ]
    out = aggregate_day_1m_to_5m(bars, day, cal)
    b0 = out[0]
    assert b0.open == 1 and b0.close == 5.5
    assert b0.high == 6 and b0.low == 0
    assert b0.volume == 50
    assert b0.is_complete  # 5/5 分钟齐


def test_incomplete_bucket_flag_and_missing_no_fill():
    day = date(2024, 6, 3)
    windows = {s.session_type: s for s in cal.sessions_for(day)}
    t0 = windows["rth"].start_utc
    # 第一个桶缺 1 根（只有 4 根 1m）
    bars = [_mk_bar(t0 + timedelta(minutes=i), o=1, h=2, lo=0.5, c=1.2) for i in (0, 1, 2, 4)]
    out = aggregate_day_1m_to_5m(bars, day, cal)
    assert len(out) == 1
    assert not out[0].is_complete
    # 第二个桶完全无数据：不输出该桶、不前向填充
    bars2 = [_mk_bar(t0 + timedelta(minutes=i), o=1, h=2, lo=0.5, c=1.2) for i in (0, 1, 2, 3)]
    out2 = aggregate_day_1m_to_5m(bars2, day, cal)
    assert len(out2) == 1


def _full_day_1m(d: date) -> list[Bar]:
    """构造某日全量 1m（价格任意但 OHLC 合法），session 按 ET 判定。"""
    bars = []
    for w in cal.sessions_for(d):
        n = int((w.end_utc - w.start_utc).total_seconds() // 60)
        for i in range(n):
            ts = w.start_utc + timedelta(minutes=i)
            bars.append(_mk_bar(ts, o=100.0, h=100.5, lo=99.5, c=100.2, session=SessionType(w.session_type)))
    return bars
