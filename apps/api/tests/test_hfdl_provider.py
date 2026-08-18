"""HFDL provider 解析器单测（离线 fixture，不依赖网络）。

覆盖：ET 墙钟→UTC 转换（冬令/夏令/DST 切换后首日）、RTH 过滤、
节假日过滤、OHLC/字段透传。
"""

from datetime import date, datetime, timedelta
from pathlib import Path

import polars as pl

from app.data_providers.hfdl_provider import parse_hfdl_parquet
from app.domain.bar import SessionType, Timeframe
from app.domain.instrument import SPY_HFDL


def _make_fixture(path: Path) -> None:
    """三个交易日 + 一个节假日 + 一根盘前bar（应被过滤）。"""
    rows = []
    # 2024-01-03（冬令 EST）：09:30 ET = 14:30 UTC
    # 2024-03-11（DST 后首个交易日 EDT）：09:30 ET = 13:30 UTC
    # 2024-07-05（夏令 EDT，常规交易日）
    # 2024-07-04（独立日休市，应整日过滤）
    for d in (date(2024, 1, 3), date(2024, 3, 11), date(2024, 7, 4), date(2024, 7, 5)):
        for i in range(390):
            t = datetime(d.year, d.month, d.day, 9, 30) + timedelta(minutes=i)
            px = 400.0 + i * 0.01
            rows.append(
                {
                    "datetime": t,
                    "open": px,
                    "high": px + 0.5,
                    "low": px - 0.5,
                    "close": px + 0.2,
                    "volume": 1000 + i,
                }
            )
    # 一根盘前 bar（09:25，防御性过滤验证）
    rows.append(
        {
            "datetime": datetime(2024, 1, 3, 9, 25),
            "open": 399.0, "high": 399.5, "low": 398.5, "close": 399.2, "volume": 10,
        }
    )
    # 列名与线上文件一致（大写 + source）
    rows = [
        {
            "datetime": r["datetime"],
            "Open": r["open"], "High": r["high"], "Low": r["low"],
            "Close": r["close"], "Volume": r["volume"],
            "source": "pitrading",
        }
        for r in rows
    ]
    pl.DataFrame(rows).write_parquet(path)


def test_parse_et_to_utc_dst_and_filters(tmp_path):
    f = tmp_path / "hfdl_SPY_clean.parquet"
    _make_fixture(f)
    bars = parse_hfdl_parquet(f, SPY_HFDL, date(2024, 1, 1), date(2024, 12, 31))

    # 3 个交易日 × 390 根，节假日与盘前被过滤
    assert len(bars) == 3 * 390
    days = sorted({b.ts_open_utc.date() for b in bars})
    assert [d.isoformat() for d in days] == ["2024-01-03", "2024-03-11", "2024-07-05"]

    # 冬令：09:30 ET = 14:30 UTC；夏令（含 DST 后首日）：09:30 ET = 13:30 UTC
    by_day = {d: [b for b in bars if b.ts_open_utc.date() == d] for d in days}
    assert by_day[date(2024, 1, 3)][0].ts_open_utc.hour == 14
    assert by_day[date(2024, 3, 11)][0].ts_open_utc.hour == 13
    assert by_day[date(2024, 7, 5)][0].ts_open_utc.hour == 13
    # 每日末根 15:55 开盘
    assert by_day[date(2024, 1, 3)][-1].ts_open_utc.hour == 20  # 15:55 EST = 20:55 UTC

    # 字段映射
    b0 = by_day[date(2024, 1, 3)][0]
    assert b0.session == SessionType.RTH
    assert b0.provider == "hfdl"
    assert b0.timeframe == Timeframe.M1
    assert b0.data_version == "hfdl-v1-clean-adjusted"
    assert b0.ts_close_utc - b0.ts_open_utc == timedelta(minutes=1)
    assert b0.open == 400.0 and b0.high == 400.5 and b0.low == 399.5


def test_parse_date_range_filter(tmp_path):
    f = tmp_path / "hfdl_SPY_clean.parquet"
    _make_fixture(f)
    bars = parse_hfdl_parquet(f, SPY_HFDL, date(2024, 3, 1), date(2024, 3, 31))
    assert len(bars) == 390
    assert {b.ts_open_utc.date() for b in bars} == {date(2024, 3, 11)}
