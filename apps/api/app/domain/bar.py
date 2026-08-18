"""K线领域对象（值对象）。时间统一 UTC 存储；session 判定以交易所时区为准。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class Timeframe(StrEnum):
    M1 = "1m"
    M5 = "5m"


class SessionType(StrEnum):
    PREMARKET = "premarket"
    RTH = "rth"
    POSTMARKET = "postmarket"


@dataclass(frozen=True, slots=True)
class Bar:
    """标准化K线。is_complete=False 的未完成K线不得进入回放（防前视）。"""

    instrument_id: str
    timeframe: Timeframe
    ts_open_utc: datetime  # tz-aware UTC
    ts_close_utc: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    session: SessionType
    provider: str
    feed: str
    data_version: str
    trade_count: int | None = None
    vwap: float | None = None
    is_complete: bool = True

    def __post_init__(self) -> None:
        if self.ts_open_utc.tzinfo is None:
            raise ValueError("ts_open_utc must be tz-aware UTC")
        if self.ts_close_utc.tzinfo is None:
            raise ValueError("ts_close_utc must be tz-aware UTC")
        if self.ts_close_utc <= self.ts_open_utc:
            raise ValueError("ts_close_utc must be after ts_open_utc")
        if not (self.low <= self.open <= self.high and self.low <= self.close <= self.high):
            raise ValueError(f"invalid OHLC: o={self.open} h={self.high} l={self.low} c={self.close}")
        if self.high < self.low:
            raise ValueError("high < low")
        if self.volume < 0:
            raise ValueError("negative volume")


def utc_now() -> datetime:
    return datetime.now(UTC)
