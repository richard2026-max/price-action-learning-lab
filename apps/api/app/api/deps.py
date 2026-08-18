"""FastAPI 依赖注入。核心领域逻辑不在路由内实现（编码原则）。"""

from __future__ import annotations

from fastapi import Request

from app.domain.instrument import Instrument
from app.replay.service import ReplayService
from app.services.analytics_service import AnalyticsService
from app.services.market_data import MarketDataStore
from app.services.scanner_service import ScannerService
from app.services.sim_trade_service import SimTradeService


def get_replay_service(request: Request) -> ReplayService:
    return request.app.state.replay_service


def get_scanner_service(request: Request) -> ScannerService:
    return request.app.state.scanner_service


def get_analytics_service(request: Request) -> AnalyticsService:
    return request.app.state.analytics_service


def get_sim_trade_service(request: Request) -> SimTradeService:
    return request.app.state.sim_trade_service


def get_store(request: Request) -> MarketDataStore:
    return request.app.state.store


def get_synth_seed(request: Request) -> int:
    return request.app.state.synth_seed


def resolve_instrument(instrument_id: str, provider: str) -> Instrument:
    from fastapi import HTTPException

    from app.domain.instrument import get_instrument

    try:
        return get_instrument(instrument_id, provider)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"未知 instrument/provider: {instrument_id}/{provider}（第一阶段仅 SPY）",
        ) from None
