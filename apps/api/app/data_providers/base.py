"""MarketDataProvider 协议（ADR-003）。

业务逻辑不直接依赖具体数据商。第一阶段正式品种仅 SPY（synthetic 演示 + alpaca 可选），
其他 provider（binance/dukascopy）属 Research Extension，仅保留抽象。
"""

from __future__ import annotations

from datetime import date
from typing import Protocol

from app.domain.bar import Bar
from app.domain.instrument import Instrument


class MarketDataProvider(Protocol):
    name: str

    def list_instruments(self) -> list[Instrument]: ...

    def fetch_1m_bars(
        self, instrument: Instrument, start: date, end: date
    ) -> list[Bar]:
        """返回 [start, end]（闭区间，交易所本地日）内的 1m K线。"""
        ...
