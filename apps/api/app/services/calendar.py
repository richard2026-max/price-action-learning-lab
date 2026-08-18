"""交易日历（XNYS / NYSE）。RTH、盘前、半日市、节假日；DST 由 zoneinfo 处理。

calendar 实现属 Product / Market Data Infrastructure（见 brooks-system-design-implications Level 0 分层）。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from functools import lru_cache
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

PREMARKET_OPEN_ET = time(4, 0)
RTH_OPEN_ET = time(9, 30)
RTH_CLOSE_ET = time(16, 0)
EARLY_CLOSE_ET = time(13, 0)  # 半日市（如 7/3、11/28、12/24）


@dataclass(frozen=True, slots=True)
class SessionWindow:
    session_type: str  # "premarket" | "rth"
    start_utc: datetime
    end_utc: datetime


class XNYSCalendar:
    """NYSE 交易日历。基于 exchange_calendars，包装为项目内协议，业务逻辑不直接依赖该库。"""

    def __init__(self, start: date = date(2010, 1, 1), end: date = date(2035, 12, 31)) -> None:
        import exchange_calendars as xcals
        import pandas as pd

        self._pd = pd
        self._cal = xcals.get_calendar("XNYS", start=start, end=end)

    def is_trading_day(self, d: date) -> bool:
        return bool(self._cal.is_session(self._pd.Timestamp(d)))

    def is_early_close(self, d: date) -> bool:
        return self._pd.Timestamp(d) in self._cal.early_closes

    def trading_days(self, start: date, end: date) -> list[date]:
        idx = self._cal.sessions_in_range(self._pd.Timestamp(start), self._pd.Timestamp(end))
        return [ts.date() for ts in idx]

    def prev_trading_day(self, d: date) -> date:
        ts = self._pd.Timestamp(d)
        if not self._cal.is_session(ts):
            raise ValueError(f"{d} is not a trading day")
        prev = self._cal.previous_session(ts)
        return prev.date()

    def next_trading_day(self, d: date) -> date:
        ts = self._pd.Timestamp(d)
        nxt = self._cal.next_session(ts)
        return nxt.date()

    def sessions_for(self, d: date) -> list[SessionWindow]:
        """返回该交易日的盘前与 RTH 窗口（UTC 边界）。聚合锚点 = 各 session 开市时间（ET 墙钟）。"""
        if not self.is_trading_day(d):
            return []
        rth_close = EARLY_CLOSE_ET if self.is_early_close(d) else RTH_CLOSE_ET
        pre_open = datetime.combine(d, PREMARKET_OPEN_ET, tzinfo=ET)
        rth_open = datetime.combine(d, RTH_OPEN_ET, tzinfo=ET)
        rth_end = datetime.combine(d, rth_close, tzinfo=ET)
        return [
            SessionWindow("premarket", pre_open.astimezone(UTC), rth_open.astimezone(UTC)),
            SessionWindow("rth", rth_open.astimezone(UTC), rth_end.astimezone(UTC)),
        ]


@lru_cache(maxsize=1)
def default_calendar() -> XNYSCalendar:
    """进程级共享实例（exchange_calendars 初始化较重）。"""
    return XNYSCalendar()
