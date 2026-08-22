"""复习调度 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.services.review_scheduler import ReviewScheduler

router = APIRouter(prefix="/reviews", tags=["reviews"])

_scheduler: ReviewScheduler | None = None


def _get_scheduler():
    global _scheduler
    if _scheduler is None:
        from app.core.config import Settings
        from app.db.session import make_engine, make_session_factory

        engine = make_engine(Settings().sqlite_path)
        factory = make_session_factory(engine)
        _scheduler = ReviewScheduler(factory=factory)
    return _scheduler


@router.get("/due")
def get_due_reviews(
    interval_days: int = Query(30, ge=7, le=180),
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    """筛选 N 天前审核过、需要盲测复评的候选列表。"""
    svc = _get_scheduler()
    return {"interval_days": interval_days, "due_reviews": svc.get_due_reviews(interval_days, limit)}
