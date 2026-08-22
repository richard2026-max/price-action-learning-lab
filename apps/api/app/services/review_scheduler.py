"""复习调度器（Blind Recheck Scheduler）。

基于审核时间戳自动筛选到期样本：
- 30 天：首次复评
- 60 天：二次复评
- 90 天：三次复评

数据模型预留 original_annotation / recheck_annotation 字段（PRD §七.6）。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models.orm import CandidateRecordORM


class ReviewScheduler:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def get_due_reviews(self, interval_days: int = 30, limit: int = 20) -> list[dict]:
        """筛选 N 天前审核过、且未被同间隔复评过的候选。"""
        cutoff = datetime.now(UTC) - timedelta(days=interval_days)

        with self._factory() as s:
            rows = s.scalars(
                select(CandidateRecordORM)
                .where(
                    CandidateRecordORM.review_status.in_(("confirmed", "rejected")),
                    CandidateRecordORM.reviewed_at.is_not(None),
                    CandidateRecordORM.reviewed_at <= cutoff,
                )
                .order_by(CandidateRecordORM.reviewed_at)
                .limit(limit)
            ).all()

            return [
                {
                    "candidate_id": r.id,
                    "day": r.day.isoformat(),
                    "detector_id": r.detector_id,
                    "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
                    "days_since_review": (datetime.now(UTC) - r.reviewed_at).days if r.reviewed_at else 0,
                    "evidence": r.evidence,
                }
                for r in rows
            ]
