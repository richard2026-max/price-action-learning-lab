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
    context_breakdown: dict[str, int]
    trade_decision_breakdown: dict[str, int]
    confidence_breakdown: dict[str, int]
    probability_breakdown: dict[str, int]


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


class TradeStatsOut(BaseModel):
    """模拟交易统计仪表盘（Level 6 交易管理训练）。"""

    total_trades: int
    closed_trades: int
    open_trades: int
    wins: int
    losses: int
    win_rate: float | None = None
    avg_pnl_in_r: float | None = None
    best_trade_r: float | None = None
    worst_trade_r: float | None = None
    avg_mfe_in_r: float | None = None
    avg_mae_in_r: float | None = None
    expectancy_in_r: float | None = None
    profit_factor: float | None = None
