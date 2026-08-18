"""确定性合成 1m 行情生成器（零密钥可跑；同 seed + 同参数 => 同数据）。

合成数据用于演示与自动测试；provider 记录为 synthetic，绝不与真实 provider 数据混用。
"""

from __future__ import annotations

import hashlib
import math
import random
from datetime import timedelta

from app.domain.bar import Bar, SessionType, Timeframe
from app.domain.instrument import Instrument
from app.services.calendar import XNYSCalendar


def _stable_int(*parts: object) -> int:
    h = hashlib.blake2b("|".join(str(p) for p in parts).encode(), digest_size=8)
    return int.from_bytes(h.digest(), "big")


def generate_day_1m(
    instrument: Instrument,
    day,
    calendar: XNYSCalendar,
    global_seed: int,
    prev_close: float | None = None,
) -> tuple[list[Bar], float]:
    """生成某交易日的 1m K线（盘前 + RTH）。返回 (bars, 当日最后收盘价)。

    prev_close 为 None 时由 seed 决定基准价（首日）。跨日连续性由调用方（generate_range）链式传递。
    """
    if not calendar.is_trading_day(day):
        return [], prev_close if prev_close is not None else 0.0

    rng = random.Random(_stable_int(global_seed, instrument.instrument_id, day.isoformat(), "v1"))
    windows = calendar.sessions_for(day)

    price = prev_close if prev_close is not None else round(400 + rng.uniform(-40, 40), 2)
    bars: list[Bar] = []
    tick = instrument.tick_size

    def snap(p: float) -> float:
        return round(round(p / tick) * tick, instrument.price_precision)

    prev_session_close = price
    for w in windows:
        # session 间跳空（RTH 相对盘前收盘，模拟 gap opening）
        gap_pct = rng.gauss(0, 0.0015) if w.session_type == "rth" else 0.0
        price = max(1.0, prev_session_close * (1 + gap_pct))

        minutes = int((w.end_utc - w.start_utc).total_seconds() // 60)
        # 日内 regime：3~6 段趋势/区间交替，制造可练习的价格行为
        regimes: list[tuple[float, float]] = []
        remaining = minutes
        while remaining > 0:
            seg = min(remaining, rng.randint(40, 130))
            drift = rng.choice([-1, -1, 0, 0, 1, 1]) * rng.uniform(0.00002, 0.00018)
            vol = rng.uniform(0.00025, 0.0012)
            regimes.append((drift, vol))
            remaining -= seg

        rth = w.session_type == "rth"
        base_vol = 900 if rth else 160
        n_reg = len(regimes)
        seg_len = minutes / n_reg  # regime 按分钟序均匀落位
        for i in range(minutes):
            drift, vol = regimes[min(n_reg - 1, int(i // seg_len))]

            o = price
            step = drift + rng.gauss(0, vol)
            c = max(0.5, o * (1 + step))
            spread = abs(rng.gauss(0, vol / 1.6))
            h = max(o, c) * (1 + spread)
            lo = min(o, c) * (1 - abs(rng.gauss(0, vol / 1.8)))
            v = max(1.0, rng.lognormvariate(math.log(base_vol), 0.55) * (1.6 if rth else 1.0))
            ts_open = w.start_utc + timedelta(minutes=i)
            bars.append(
                Bar(
                    instrument_id=instrument.instrument_id,
                    timeframe=Timeframe.M1,
                    ts_open_utc=ts_open,
                    ts_close_utc=ts_open + timedelta(minutes=1),
                    open=snap(o),
                    high=snap(h),
                    low=snap(lo),
                    close=snap(c),
                    volume=round(v, 2),
                    session=SessionType(w.session_type),
                    provider=instrument.provider,
                    feed=instrument.feed,
                    data_version="synthetic-v1",
                    trade_count=int(v / rng.uniform(8, 20)),
                    is_complete=True,
                )
            )
            price = c
        prev_session_close = price

    return bars, price


def generate_range_1m(
    instrument: Instrument,
    start,
    end,
    calendar: XNYSCalendar,
    global_seed: int,
) -> list[Bar]:
    """按交易日顺序生成一段 1m 数据（价格跨日连续，便于形成真实的前日高低收关系）。"""
    out: list[Bar] = []
    prev_close: float | None = None
    for day in calendar.trading_days(start, end):
        bars, prev_close = generate_day_1m(instrument, day, calendar, global_seed, prev_close)
        out.extend(bars)
    return out
