"""数据管理路由：数据集清单、合成数据 seed、交易日历查询。"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.deps import get_current_user, get_store, get_synth_seed
from app.models.orm import UserORM
from app.schemas.data import SeedIn, SeedOut
from app.services.calendar import default_calendar
from app.services.data_seed_service import run_seed
from app.services.market_data import MarketDataStore

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/datasets")
def list_datasets(
    store: MarketDataStore = Depends(get_store),
    _user: UserORM = Depends(get_current_user),
) -> list[dict]:
    return store.list_datasets()


@router.post("/seed", response_model=SeedOut)
def seed(
    req: SeedIn,
    request: Request,
    store: MarketDataStore = Depends(get_store),
    synth_seed: int = Depends(get_synth_seed),
) -> SeedOut:
    """生成合成 SPY 1m 数据并聚合 5m（零密钥演示路径；幂等，重复数据自动去重）。"""
    if not request.app.state.settings.debug:
        raise HTTPException(403, "数据生成属于本地运维操作，生产环境不可用")
    return run_seed(store=store, synth_seed=synth_seed, req=req)


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
