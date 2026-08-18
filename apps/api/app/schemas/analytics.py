"""学习分析与盲测复评相关 Pydantic Schemas（Product / Learning Analytics）。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BehaviorStats(BaseModel):
    total_sessions: int
    completed_sessions: int
    total_judgments: int
    total_annotations: int
    total_reviewed_candidates: int
    total_confirmed_positives: int
    total_rejected_negatives: int
    total_favorites: int
    total_mistakes: int


class JudgmentDistribution(BaseModel):
    context_breakdown: dict[str, int]  # trend_up, trend_down, trading_range, transition
    trade_decision_breakdown: dict[str, int]  # long, short, none
    confidence_breakdown: dict[str, int]  # good, okay, bad
    probability_breakdown: dict[str, int]  # good, okay, bad


class RejectionReasonStats(BaseModel):
    reason_counts: dict[str, int]


class BlindRecheckItem(BaseModel):
    candidate_id: str
    instrument_id: str
    provider: str
    day: str
    bar_index: int
    bar_time_utc: datetime
    detector_id: str
    # 盲测关键：隐藏原始审核结果与笔记
    evidence: dict


class SubmitRecheckIn(BaseModel):
    candidate_id: str
    recheck_status: str = Field(..., pattern="^(confirmed|rejected|uncertain|needs_review)$")
    recheck_notes: str | None = None


class RecheckCompareResult(BaseModel):
    candidate_id: str
    original_status: str
    recheck_status: str
    is_consistent: bool
    original_reviewed_at: datetime | None
    rechecked_at: datetime
    original_notes: str | None
    recheck_notes: str | None


class AnalyticsOverviewOut(BaseModel):
    behavior: BehaviorStats
    judgment: JudgmentDistribution
    rejections: RejectionReasonStats
    recent_mistakes: list[dict]
    recent_favorites: list[dict]
