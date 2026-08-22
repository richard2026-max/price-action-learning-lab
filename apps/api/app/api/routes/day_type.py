"""日类型分类与复习调度 API 路由。"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_store
from app.domain.bar import SessionType, Timeframe
from app.services.day_type_service import classify_day
from app.services.market_data import MarketDataStore

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/day-type")
def classify_day_type(
    day: str = Query(..., description="YYYY-MM-DD"),
    provider: str = "synthetic",
    instrument_id: str = "SPY",
    store: MarketDataStore = Depends(get_store),
) -> dict:
    """对已完成交易日进行日类型分类（仅用于复盘分析）。"""
    from app.domain.instrument import get_instrument

    try:
        instrument = get_instrument(instrument_id, provider)
    except KeyError:
        raise HTTPException(404, detail=f"未知 instrument/provider: {instrument_id}/{provider}") from None

    d = date.fromisoformat(day)
    bars = store.read_day(instrument, Timeframe.M5, d, SessionType.RTH)
    if not bars:
        raise HTTPException(404, detail=f"{day} 无 RTH 5m 数据")

    result = classify_day(bars)
    return {
        "day": day,
        "day_type": result.day_type,
        "confidence": result.confidence,
        **result.evidence,
    }
