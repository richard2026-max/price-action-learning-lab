"""合成演示数据 provider（零密钥可跑；确定性可复现）。"""

from __future__ import annotations

from datetime import date

from app.domain.bar import Bar
from app.domain.instrument import SPY_SYNTH, Instrument
from app.services.calendar import default_calendar
from app.services.synthetic import generate_range_1m


class SyntheticProvider:
    name = "synthetic"

    def __init__(self, seed: int) -> None:
        self._seed = seed
        self._cal = default_calendar()

    def list_instruments(self) -> list[Instrument]:
        return [SPY_SYNTH]

    def fetch_1m_bars(self, instrument: Instrument, start: date, end: date) -> list[Bar]:
        if instrument.provider != "synthetic":
            raise ValueError(f"synthetic provider 不支持 {instrument.provider}")
        return generate_range_1m(instrument, start, end, self._cal, self._seed)
