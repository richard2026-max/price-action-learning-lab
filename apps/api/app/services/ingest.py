"""摄取服务：真实/合成 1m 数据 → 聚合 5m → 入库 + manifest。"""

from __future__ import annotations

from app.domain.bar import Timeframe
from app.domain.instrument import Instrument
from app.services.aggregation import aggregate_day_1m_to_5m
from app.services.calendar import ET, default_calendar
from app.services.market_data import MarketDataStore


def ingest_bars(
    store: MarketDataStore,
    instrument: Instrument,
    bars_1m: list,
    start,
    end,
) -> dict:
    """通用入库：1m 写入 + 按交易日聚合 5m 写入 + manifest。幂等（重复自动去重）。"""
    cal = default_calendar()
    days = cal.trading_days(start, end)
    bars_5m: list = []
    for day in days:
        day_1m = [b for b in bars_1m if b.ts_open_utc.astimezone(ET).date() == day]
        bars_5m.extend(aggregate_day_1m_to_5m(day_1m, day, cal))

    r1 = store.write_bars(bars_1m, instrument, Timeframe.M1)
    r5 = store.write_bars(bars_5m, instrument, Timeframe.M5)
    return {
        "days": len(days),
        "bars_1m": len(bars_1m),
        "bars_5m": len(bars_5m),
        "duplicate_1m": r1["duplicate_count"],
        "duplicate_5m": r5["duplicate_count"],
        "manifest_5m": store.list_datasets(),
    }
