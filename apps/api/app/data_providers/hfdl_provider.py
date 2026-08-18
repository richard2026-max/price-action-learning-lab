"""HF Data Library provider（免费 SPY 1m 历史数据，CC BY 4.0）。

数据特征（docs/pages 方法论，调研结论沉淀）：
- 仅 RTH 09:30-16:00 ET，无盘前/盘后（回放关键价位中 premarket 自动降级为 None）；
- 复权价格（split/dividend adjusted，无未复权选项）——绝对价位与除息跳空有偏差；
- 时段精度：2002~2022-03 为 PiTrading 合并磁带（CTA/UTP 全市场），之后为 IEX 单所
  （high/low 可能缺失其他交易所极值，OQ-01 标注待验证）；
- datetime 为 ET 墙钟（naive），本 provider 负责 tz-aware 化并转 UTC（DST 由 zoneinfo 处理；
  RTH 时段无秋令时歧义时间）。

API（https://hfdatalibrary.com/pages/api）：X-API-Key 头鉴权；
GET /download/{ticker}?version=clean 返回全历史单文件 Parquet（R2 直链，~50MB for SPY）。
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import polars as pl

from app.domain.bar import Bar, SessionType, Timeframe
from app.domain.instrument import Instrument

ET = ZoneInfo("America/New_York")
RTH_OPEN = time(9, 30)
RTH_CLOSE = time(16, 0)
DATA_VERSION = "hfdl-v1-clean-adjusted"


class HFDLError(RuntimeError):
    pass


def parse_hfdl_parquet(
    path: Path, instrument: Instrument, start: date, end: date
) -> list[Bar]:
    """解析 HFDL 全历史 Parquet → 标准化 1m Bar 列表（UTC，session=rth）。

    与网络解耦，便于用 fixture 单测。
    """
    from app.services.calendar import default_calendar

    cal = default_calendar()
    df = pl.read_parquet(path)
    # 实际文件列名为大写（Open/High/Low/Close/Volume）+ source（pitrading|iex）
    df = df.rename({c: c.lower() for c in df.columns})
    required = {"datetime", "open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise HFDLError(f"parquet 缺少列: {missing}，实际列: {df.columns}")

    df = df.sort("datetime")
    # ET 墙钟(naive) → tz-aware ET → UTC
    df = df.with_columns(
        pl.col("datetime").dt.replace_time_zone("America/New_York")
        .dt.convert_time_zone("UTC")
        .alias("ts_open_utc")
    )
    df = df.filter(
        (pl.col("datetime").dt.date() >= start) & (pl.col("datetime").dt.date() <= end)
    )

    trading = set(cal.trading_days(start, end))
    out: list[Bar] = []
    for row in df.iter_rows(named=True):
        d = row["datetime"].date()
        if d not in trading:
            continue
        t = row["datetime"].time()
        if not (RTH_OPEN <= t < RTH_CLOSE):
            continue  # 理论上 clean 版无盘前；防御性过滤
        out.append(
            Bar(
                instrument_id=instrument.instrument_id,
                timeframe=Timeframe.M1,
                ts_open_utc=row["ts_open_utc"],
                ts_close_utc=row["ts_open_utc"] + timedelta(minutes=1),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
                session=SessionType.RTH,
                provider=instrument.provider,
                feed=instrument.feed,
                data_version=DATA_VERSION,
                is_complete=True,
            )
        )
    return out


class HFDLProvider:
    name = "hfdl"

    def __init__(self, api_key: str | None, base_url: str = "https://api.hfdatalibrary.com/v1",
                 cache_dir: Path | None = None) -> None:
        if not api_key:
            raise HFDLError("HFDL API key 未配置（PALL_HFDL_API_KEY）。")
        self._key = api_key
        self._base = base_url.rstrip("/")
        self._cache_dir = cache_dir

    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self._key}

    def download_full_history(self, instrument: Instrument, version: str = "clean") -> Path:
        """下载某标的的全历史 1m Parquet 到缓存目录（已存在则复用）。"""
        if self._cache_dir is None:
            raise HFDLError("cache_dir 未配置")
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        dest = self._cache_dir / f"hfdl_{instrument.symbol}_{version}.parquet"
        if dest.exists() and dest.stat().st_size > 0:
            return dest
        url = f"{self._base}/download/{instrument.symbol}"
        with httpx.Client(headers=self._headers(), timeout=300) as client:
            with client.stream("GET", url, params={"version": version}) as resp:
                if resp.status_code != 200:
                    body = resp.read()[:300]
                    raise HFDLError(f"hfdl {resp.status_code}: {body!r}")
                with open(dest, "wb") as f:
                    for chunk in resp.iter_bytes(1 << 20):
                        f.write(chunk)
        return dest

    def list_instruments(self) -> list[Instrument]:
        from app.domain.instrument import SPY_HFDL

        return [SPY_HFDL]

    def fetch_1m_bars(self, instrument: Instrument, start: date, end: date) -> list[Bar]:
        if instrument.provider != "hfdl":
            raise HFDLError(f"hfdl provider 不支持 {instrument.provider}")
        path = self.download_full_history(instrument)
        return parse_hfdl_parquet(path, instrument, start, end)


def verify_splice_boundary(bars: list[Bar]) -> dict:
    """诊断用：报告 2022-03 前后（合并磁带→IEX）的成交量变化，辅助 OQ-01 验证。"""
    boundary = datetime(2022, 3, 1, tzinfo=ET)
    pre = [b.volume for b in bars if b.ts_open_utc.astimezone(ET) < boundary]
    post = [b.volume for b in bars if b.ts_open_utc.astimezone(ET) >= boundary]
    return {
        "pre_2022_03_bars": len(pre),
        "pre_2022_03_avg_volume": sum(pre) / len(pre) if pre else None,
        "post_2022_03_bars": len(post),
        "post_2022_03_avg_volume": sum(post) / len(post) if post else None,
    }
