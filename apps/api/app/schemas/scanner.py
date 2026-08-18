"""Scanner 相关的 Pydantic Schemas（MVP-D）。"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ReviewStatus(StrEnum):
    UNREVIEWED = "unreviewed"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    UNCERTAIN = "uncertain"
    NEEDS_REVIEW = "needs_review"


class RejectionReason(StrEnum):
    CONTEXT_MISMATCH = "context_mismatch"
    MECHANICAL_FLAW = "mechanical_flaw"
    DATA_QUALITY = "data_quality"
    AMBIGUOUS_PATTERN = "ambiguous_pattern"
    CONFLICTS_WITH_BOOK = "conflicts_with_book"
    OTHER = "other"


class CreateScanTaskIn(BaseModel):
    instrument_id: str = "SPY"
    provider: str = "synthetic"
    start_day: str = Field(..., description="YYYY-MM-DD")
    end_day: str = Field(..., description="YYYY-MM-DD")
    timeframe: str = "5m"
    detector_ids: list[str] = Field(default_factory=list, description="留空则扫描全部已注册 detector")
    include_sealed: bool = Field(False, description="是否包含封存考试日（默认严格排除）")


class ScanTaskOut(BaseModel):
    id: str
    instrument_id: str
    provider: str
    timeframe: str
    start_day: date
    end_day: date
    detector_ids: list[str]
    status: str
    progress: float
    total_days: int
    scanned_days: int
    scanned_bars: int
    candidate_count: int
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class CandidateRecordOut(BaseModel):
    id: str
    task_id: str
    instrument_id: str
    provider: str
    day: date
    bar_index: int
    bar_time_utc: datetime
    detector_id: str
    detector_version: str
    result_type: str
    result: object
    evidence: dict
    rule_source: str
    provenance: str
    review_status: str
    rejection_reason: str | None
    review_notes: str | None
    is_favorite: bool
    is_mistake_notebook: bool
    reviewed_at: datetime | None
    created_at: datetime


class ReviewCandidateIn(BaseModel):
    review_status: ReviewStatus
    rejection_reason: RejectionReason | None = None
    review_notes: str | None = None
    is_favorite: bool | None = None
    is_mistake_notebook: bool | None = None
