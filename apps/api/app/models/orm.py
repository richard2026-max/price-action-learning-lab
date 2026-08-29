"""SQLAlchemy ORM 模型（事务型应用数据：回放、判断、标注、扫描任务、候选记录、模拟交易）。"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class UserORM(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("provider", "subject", name="uq_users_provider_subject"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    provider: Mapped[str] = mapped_column(String(16))
    subject: Mapped[str] = mapped_column(String(128))
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class ReplaySessionORM(Base):
    __tablename__ = "replay_sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # uuid4 hex
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    instrument_id: Mapped[str] = mapped_column(String(16))
    provider: Mapped[str] = mapped_column(String(16))
    day: Mapped[date] = mapped_column(Date)
    timeframe: Mapped[str] = mapped_column(String(4))  # '5m'
    mode: Mapped[str] = mapped_column(String(16))  # free | hidden_answer | exam
    sampling_mode: Mapped[str] = mapped_column(String(24), default="user_initiated")
    warmup_bars: Mapped[int] = mapped_column(Integer, default=6)
    cursor_index: Mapped[int] = mapped_column(Integer, default=0)
    cursor_version: Mapped[int] = mapped_column(Integer, default=0)
    state: Mapped[str] = mapped_column(String(16), default="running")  # running|completed
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class ReplayAdvanceRequestORM(Base):
    __tablename__ = "replay_advance_requests"
    __table_args__ = (UniqueConstraint("session_id", "request_id", name="uq_replay_advance_request"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("replay_sessions.id", ondelete="CASCADE"), index=True)
    request_id: Mapped[str] = mapped_column(String(128))
    requested_n: Mapped[int] = mapped_column(Integer)
    expected_cursor_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result_cursor_index: Mapped[int] = mapped_column(Integer)
    result_cursor_version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class JudgmentORM(Base):
    """Predict First 判断。提交即锁定（无更新接口）；bar_index = 提交时服务端 cursor。"""

    __tablename__ = "judgments"
    __table_args__ = (UniqueConstraint("session_id", "client_request_id", name="uq_judgment_request"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("replay_sessions.id", ondelete="CASCADE"))
    bar_index: Mapped[int] = mapped_column(Integer)
    bar_time_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    client_request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class AnnotationORM(Base):
    __tablename__ = "annotations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("replay_sessions.id", ondelete="CASCADE"))
    bar_index: Mapped[int] = mapped_column(Integer)
    bar_time_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    kind: Mapped[str] = mapped_column(String(16))  # label | note
    label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class ScanTaskORM(Base):
    """扫描任务状态持久化（MVP-D 异步本地任务管理）。"""

    __tablename__ = "scan_tasks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # uuid4 hex
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    instrument_id: Mapped[str] = mapped_column(String(16))
    provider: Mapped[str] = mapped_column(String(16))
    timeframe: Mapped[str] = mapped_column(String(4), default="5m")
    start_day: Mapped[date] = mapped_column(Date)
    end_day: Mapped[date] = mapped_column(Date)
    detector_ids: Mapped[list] = mapped_column(JSON)  # 指定扫描哪些 detector
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|running|completed|failed
    progress: Mapped[float] = mapped_column(Float, default=0.0)  # 0.0 - 1.0
    total_days: Mapped[int] = mapped_column(Integer, default=0)
    scanned_days: Mapped[int] = mapped_column(Integer, default=0)
    scanned_bars: Mapped[int] = mapped_column(Integer, default=0)
    candidate_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class CandidateRecordORM(Base):
    """扫描生成的候选持久化记录，支持人工审核（4 档标记）、错题本与收藏。"""

    __tablename__ = "candidate_records"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # uuid4 hex
    task_id: Mapped[str] = mapped_column(ForeignKey("scan_tasks.id", ondelete="CASCADE"), index=True)
    instrument_id: Mapped[str] = mapped_column(String(16))
    provider: Mapped[str] = mapped_column(String(16))
    day: Mapped[date] = mapped_column(Date, index=True)
    bar_index: Mapped[int] = mapped_column(Integer)
    bar_time_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    detector_id: Mapped[str] = mapped_column(String(32), index=True)
    detector_version: Mapped[str] = mapped_column(String(16))
    result_type: Mapped[str] = mapped_column(String(16))
    result: Mapped[dict | str | bool | float | int | list] = mapped_column(JSON)
    evidence: Mapped[dict] = mapped_column(JSON)
    rule_source: Mapped[str] = mapped_column(String(32))
    provenance: Mapped[str] = mapped_column(String(32))

    # 人工审核与标注状态：unreviewed | confirmed | rejected | uncertain | needs_review
    review_status: Mapped[str] = mapped_column(String(16), default="unreviewed")
    rejection_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    is_mistake_notebook: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class SimTradeORM(Base):
    """模拟交易记录（Level 6 交易管理训练）。

    支持市价单、限价单与停止单；撮合规则默认保守（pessimistic）；
    实时追踪 MFE（最大有利位移）与 MAE（最大不利位移）。
    """

    __tablename__ = "sim_trades"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # uuid4 hex
    session_id: Mapped[str] = mapped_column(ForeignKey("replay_sessions.id", ondelete="CASCADE"), index=True)
    instrument_id: Mapped[str] = mapped_column(String(16))
    provider: Mapped[str] = mapped_column(String(16))
    day: Mapped[date] = mapped_column(Date)
    side: Mapped[str] = mapped_column(String(8))  # "long" | "short"
    order_type: Mapped[str] = mapped_column(String(16))  # "market" | "limit" | "stop"
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | open | closed | cancelled

    # 计划与成交价格
    order_bar_index: Mapped[int] = mapped_column(Integer)
    order_time_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    planned_entry_price: Mapped[float] = mapped_column(Float)
    actual_entry_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    entry_bar_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    entry_time_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # 风险与目标管理（Brooks 交易方程式）
    stop_price: Mapped[float] = mapped_column(Float)  # 失效点
    target_price: Mapped[float] = mapped_column(Float)  # 目标止盈
    initial_risk: Mapped[float] = mapped_column(Float)  # |entry - stop|

    # 出场与收益统计
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    exit_bar_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exit_time_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    exit_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)  # target | stop | manual | eod
    pnl: Mapped[float | None] = mapped_column(Float, nullable=True)
    pnl_in_r: Mapped[float | None] = mapped_column(Float, nullable=True)  # PnL / initial_risk

    # 路径保真统计 (MFE / MAE)
    mfe_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    mfe_in_r: Mapped[float | None] = mapped_column(Float, nullable=True)
    mae_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    mae_in_r: Mapped[float | None] = mapped_column(Float, nullable=True)

    # 逻辑与笔记
    setup_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
