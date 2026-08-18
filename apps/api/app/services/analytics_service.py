"""学习分析与认知统计引擎（AnalyticsService）。

提供：
1. 学习行为与训练总量统计；
2. 市场环境判断分布与交易意图统计；
3. 候选形态人工审核正反例与拒绝原因归纳；
4. 盲测复评（Blind Recheck）调度与一致性（test-retest consistency）对比。
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.models.orm import AnnotationORM, CandidateRecordORM, JudgmentORM, ReplaySessionORM
from app.schemas.analytics import (
    AnalyticsOverviewOut,
    BehaviorStats,
    BlindRecheckItem,
    JudgmentDistribution,
    RecheckCompareResult,
    RejectionReasonStats,
    SubmitRecheckIn,
)


class AnalyticsService:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def get_overview(self) -> AnalyticsOverviewOut:
        with self._factory() as s:
            total_sessions = s.scalar(select(func.count(ReplaySessionORM.id))) or 0
            completed_sessions = s.scalar(
                select(func.count(ReplaySessionORM.id)).where(ReplaySessionORM.state == "completed")
            ) or 0
            total_judgments = s.scalar(select(func.count(JudgmentORM.id))) or 0
            total_annotations = s.scalar(select(func.count(AnnotationORM.id))) or 0

            # 候选审核统计
            c_stmt = select(func.count(CandidateRecordORM.id))
            total_reviewed = s.scalar(c_stmt.where(CandidateRecordORM.review_status != "unreviewed")) or 0
            total_confirmed = s.scalar(c_stmt.where(CandidateRecordORM.review_status == "confirmed")) or 0
            total_rejected = s.scalar(c_stmt.where(CandidateRecordORM.review_status == "rejected")) or 0
            total_favs = s.scalar(c_stmt.where(CandidateRecordORM.is_favorite.is_(True))) or 0
            total_mistakes = s.scalar(c_stmt.where(CandidateRecordORM.is_mistake_notebook.is_(True))) or 0

            # 判断分布统计
            judgments = s.scalars(select(JudgmentORM)).all()
            ctx_counter: Counter[str] = Counter()
            dir_counter: Counter[str] = Counter()
            conf_counter: Counter[str] = Counter()
            prob_counter: Counter[str] = Counter()

            for j in judgments:
                p = j.payload or {}
                ctx_counter[p.get("context_label", "transition")] += 1
                dir_counter[p.get("direction", "none")] += 1
                conf_counter[p.get("confidence", "okay")] += 1
                prob_counter[p.get("probability_estimate", "okay")] += 1

            # 拒绝原因统计
            rejections = s.scalars(
                select(CandidateRecordORM.rejection_reason).where(CandidateRecordORM.review_status == "rejected")
            ).all()
            reason_counter: Counter[str] = Counter(r for r in rejections if r)

            # 近期错题与收藏
            recent_mistakes_orm = s.scalars(
                select(CandidateRecordORM)
                .where(CandidateRecordORM.is_mistake_notebook.is_(True))
                .order_by(desc(CandidateRecordORM.reviewed_at))
                .limit(10)
            ).all()
            recent_favorites_orm = s.scalars(
                select(CandidateRecordORM)
                .where(CandidateRecordORM.is_favorite.is_(True))
                .order_by(desc(CandidateRecordORM.reviewed_at))
                .limit(10)
            ).all()

            return AnalyticsOverviewOut(
                behavior=BehaviorStats(
                    total_sessions=total_sessions,
                    completed_sessions=completed_sessions,
                    total_judgments=total_judgments,
                    total_annotations=total_annotations,
                    total_reviewed_candidates=total_reviewed,
                    total_confirmed_positives=total_confirmed,
                    total_rejected_negatives=total_rejected,
                    total_favorites=total_favs,
                    total_mistakes=total_mistakes,
                ),
                judgment=JudgmentDistribution(
                    context_breakdown=dict(ctx_counter),
                    trade_decision_breakdown=dict(dir_counter),
                    confidence_breakdown=dict(conf_counter),
                    probability_breakdown=dict(prob_counter),
                ),
                rejections=RejectionReasonStats(reason_counts=dict(reason_counter)),
                recent_mistakes=[{
                    "id": m.id, "day": m.day.isoformat(), "bar_index": m.bar_index,
                    "detector_id": m.detector_id, "rejection_reason": m.rejection_reason,
                    "notes": m.review_notes, "reviewed_at": m.reviewed_at.isoformat() if m.reviewed_at else None
                } for m in recent_mistakes_orm],
                recent_favorites=[{
                    "id": f.id, "day": f.day.isoformat(), "bar_index": f.bar_index,
                    "detector_id": f.detector_id, "notes": f.review_notes,
                    "reviewed_at": f.reviewed_at.isoformat() if f.reviewed_at else None
                } for f in recent_favorites_orm],
            )

    def get_blind_recheck_queue(self, limit: int = 20) -> list[BlindRecheckItem]:
        """提取过去已审核过的候选作为盲测样本（严格脱敏原始审核标签与笔记）。"""
        with self._factory() as s:
            rows = s.scalars(
                select(CandidateRecordORM)
                .where(CandidateRecordORM.review_status.in_(("confirmed", "rejected")))
                .order_by(func.random())
                .limit(limit)
            ).all()
            return [
                BlindRecheckItem(
                    candidate_id=r.id,
                    instrument_id=r.instrument_id,
                    provider=r.provider,
                    day=r.day.isoformat(),
                    bar_index=r.bar_index,
                    bar_time_utc=r.bar_time_utc,
                    detector_id=r.detector_id,
                    evidence=r.evidence,
                )
                for r in rows
            ]

    def submit_recheck(self, req: SubmitRecheckIn) -> RecheckCompareResult:
        """提交盲测复评结论并揭晓前后一致性对比。"""
        with self._factory() as s:
            orm = s.get(CandidateRecordORM, req.candidate_id)
            if not orm:
                raise ValueError("Candidate not found")

            orig_status = orm.review_status
            is_consistent = (orig_status == req.recheck_status)

            return RecheckCompareResult(
                candidate_id=orm.id,
                original_status=orig_status,
                recheck_status=req.recheck_status,
                is_consistent=is_consistent,
                original_reviewed_at=orm.reviewed_at,
                rechecked_at=datetime.now(UTC),
                original_notes=orm.review_notes,
                recheck_notes=req.recheck_notes,
            )
