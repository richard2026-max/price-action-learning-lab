"""数据管理路由：数据集清单、合成数据 seed、交易日历查询。"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_store, get_synth_seed
from app.data_providers.synthetic_provider import SyntheticProvider
from app.domain.bar import Timeframe
from app.domain.instrument import SPY_SYNTH
from app.schemas.data import SeedIn, SeedOut
from app.services.aggregation import aggregate_day_1m_to_5m
from app.services.calendar import ET, default_calendar
from app.services.market_data import MarketDataStore

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/datasets")
def list_datasets(store: MarketDataStore = Depends(get_store)) -> list[dict]:
    return store.list_datasets()


@router.post("/seed", response_model=SeedOut)
def seed(
    req: SeedIn,
    store: MarketDataStore = Depends(get_store),
    synth_seed: int = Depends(get_synth_seed),
) -> SeedOut:
    """生成合成 SPY 1m 数据并聚合 5m（零密钥演示路径；幂等，重复数据自动去重）。"""
    try:
        start, end = date.fromisoformat(req.start), date.fromisoformat(req.end)
    except ValueError as e:
        raise HTTPException(422, f"日期格式错误: {e}") from e
    if start > end:
        raise HTTPException(422, "start 不能晚于 end")

    provider = SyntheticProvider(seed=req.seed if req.seed is not None else synth_seed)
    cal = default_calendar()
    instrument = SPY_SYNTH
    days = cal.trading_days(start, end)

    bars_1m = provider.fetch_1m_bars(instrument, start, end)
    bars_5m: list = []
    for day in days:
        day_1m = [b for b in bars_1m if b.ts_open_utc.astimezone(ET).date() == day]
        bars_5m.extend(aggregate_day_1m_to_5m(day_1m, day, cal))

    r1 = store.write_bars(bars_1m, instrument, Timeframe.M1)
    r5 = store.write_bars(bars_5m, instrument, Timeframe.M5)
    m1 = store.list_datasets()
    manifest_1m = next(
        (m for m in m1 if m["provider"] == "synthetic" and m["timeframe"] == "1m"), {}
    )
    manifest_5m = next(
        (m for m in m1 if m["provider"] == "synthetic" and m["timeframe"] == "5m"), {}
    )
    return SeedOut(
        days=len(days),
        bars_1m=len(bars_1m),
        bars_5m=len(bars_5m),
        duplicate_count_1m=r1.get("duplicate_count", 0),
        duplicate_count_5m=r5.get("duplicate_count", 0),
        manifest_1m=manifest_1m,
        manifest_5m=manifest_5m,
    )


@router.get("/calendar")
def calendar_days(
    start: str = Query(...), end: str = Query(...), early_closes: bool = False
) -> dict:
    cal = default_calendar()
    try:
        s, e = date.fromisoformat(start), date.fromisoformat(end)
    except ValueError as exc:
        raise HTTPException(422, f"日期格式错误: {exc}") from exc
    days = cal.trading_days(s, e)
    if early_closes:
        return {"days": [d.isoformat() for d in days],
                "early_closes": [d.isoformat() for d in days if cal.is_early_close(d)]}
    return {"days": [d.isoformat() for d in days]}
