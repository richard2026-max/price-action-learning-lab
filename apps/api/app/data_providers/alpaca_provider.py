"""Alpaca 历史行情 provider（SPY 1m；市场数据密钥，与交易密钥在设计上分离）。

密钥缺失时构造抛错——应用仍可用 synthetic 演示数据启动（单点失败兜底，风险清单 #12）。
feed（iex/sip）记录进 Instrument 与 manifest，不静默混用。
OQ-01：该 feed 是否满足"一跳"精度待 MVP-C 前验证。
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import httpx

from app.domain.bar import Bar, SessionType, Timeframe
from app.domain.instrument import Instrument

_BASE = "https://data.alpaca.markets"


class AlpacaProviderError(RuntimeError):
    pass


class AlpacaProvider:
    name = "alpaca"

    def __init__(self, key_id: str | None, secret_key: str | None, feed: str = "iex") -> None:
        if not key_id or not secret_key:
            raise AlpacaProviderError(
                "Alpaca 密钥未配置（PALL_ALPACA_KEY_ID / PALL_ALPACA_SECRET_KEY）。"
                "无密钥时请使用 synthetic 演示数据。"
            )
        self._headers = {"APCA-API-KEY-ID": key_id, "APCA-API-SECRET-KEY": secret_key}
        self._feed = feed

    def fetch_1m_bars(self, instrument: Instrument, start: date, end: date) -> list[Bar]:
        """分页拉取 1m bars。session 归属按 ET 墙钟判定（09:30 起为 RTH，之前为 premarket）。"""
        from datetime import time as dtime
        from datetime import timedelta

        from app.services.calendar import ET, default_calendar

        cal = default_calendar()
        out: list[Bar] = []
        url = f"{_BASE}/v2/stocks/{instrument.symbol}/bars"
        params: dict[str, str] = {
            "timeframe": "1Min",
            "start": f"{start.isoformat()}T00:00:00Z",
            "end": f"{end.isoformat()}T23:59:59Z",
            "feed": self._feed,
            "limit": "10000",
        }
        with httpx.Client(headers=self._headers, timeout=30) as client:
            while True:
                resp = client.get(url, params=params)
                if resp.status_code != 200:
                    raise AlpacaProviderError(f"alpaca {resp.status_code}: {resp.text[:200]}")
                payload = resp.json()
                for row in payload.get("bars", []):
                    ts = datetime.fromisoformat(row["t"].replace("Z", "+00:00")).astimezone(UTC)
                    session = (
                        SessionType.RTH
                        if ts.astimezone(ET).time() >= dtime(9, 30)
                        else SessionType.PREMARKET
                    )
                    out.append(
                        Bar(
                            instrument_id=instrument.instrument_id,
                            timeframe=Timeframe.M1,
                            ts_open_utc=ts,
                            ts_close_utc=ts + timedelta(minutes=1),
                            open=float(row["o"]), high=float(row["h"]),
                            low=float(row["l"]), close=float(row["c"]),
                            volume=float(row.get("v") or 0),
                            session=session,
                            provider=instrument.provider,
                            feed=self._feed,
                            data_version=f"alpaca-{self._feed}",
                            trade_count=row.get("n"),
                        )
                    )
                token = payload.get("next_page_token")
                if not token:
                    break
                params["page_token"] = token
        # 休市日过滤
        return [b for b in out if cal.is_trading_day(b.ts_open_utc.astimezone(ET).date())]
