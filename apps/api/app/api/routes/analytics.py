"""学习分析、盲测复评与交易统计 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_analytics_service, get_current_user
from app.models.orm import UserORM
from app.schemas.analytics import (
    AnalyticsOverviewOut,
    BlindRecheckItem,
    RecheckCompareResult,
    SubmitRecheckIn,
    TradeStatsOut,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverviewOut)
def get_overview(
    svc: AnalyticsService = Depends(get_analytics_service),
    user: UserORM = Depends(get_current_user),
) -> AnalyticsOverviewOut:
    return svc.get_overview(user.id)


@router.get("/trade-stats", response_model=TradeStatsOut)
def get_trade_stats(
    svc: AnalyticsService = Depends(get_analytics_service),
    user: UserORM = Depends(get_current_user),
) -> TradeStatsOut:
    return TradeStatsOut(**svc.get_trade_stats(user.id))


@router.get("/recheck-queue", response_model=list[BlindRecheckItem])
def get_recheck_queue(
    limit: int = Query(20, ge=1, le=100),
    svc: AnalyticsService = Depends(get_analytics_service),
    user: UserORM = Depends(get_current_user),
) -> list[BlindRecheckItem]:
    return svc.get_blind_recheck_queue(user.id, limit=limit)


@router.post("/recheck", response_model=RecheckCompareResult)
def submit_recheck(
    req: SubmitRecheckIn,
    svc: AnalyticsService = Depends(get_analytics_service),
    user: UserORM = Depends(get_current_user),
) -> RecheckCompareResult:
    try:
        return svc.submit_recheck(req, user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
