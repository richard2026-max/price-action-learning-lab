"""模拟交易相关 Pydantic Schemas（MVP 交易管理与 MFE/MAE 统计）。"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class TradeSide(StrEnum):
    LONG = "long"
    SHORT = "short"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class TradeStatus(StrEnum):
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class ExitReason(StrEnum):
    TARGET = "target"
    STOP = "stop"
    MANUAL = "manual"
    EOD = "eod"


class CreateSimTradeIn(BaseModel):
    side: TradeSide
    order_type: OrderType = OrderType.MARKET
    planned_entry_price: float = Field(..., gt=0)
    stop_price: float = Field(..., gt=0, description="失效点 (Stop)")
    target_price: float = Field(..., gt=0, description="目标位 (Target)")
    setup_notes: str | None = None
    reasons: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_risk(self) -> CreateSimTradeIn:
        if self.side == TradeSide.LONG:
            if not (self.stop_price < self.planned_entry_price < self.target_price):
                raise ValueError("多头交易必须满足：止损 < 计划入场 < 目标位")
        else:
            if not (self.target_price < self.planned_entry_price < self.stop_price):
                raise ValueError("空头交易必须满足：目标位 < 计划入场 < 止损")
        return self


class ManualExitTradeIn(BaseModel):
    exit_price: float | None = None  # None 则以当前 bar close 成交
    notes: str | None = None


class SimTradeOut(BaseModel):
    id: str
    session_id: str
    instrument_id: str
    provider: str
    day: date
    side: str
    order_type: str
    status: str
    order_bar_index: int
    order_time_utc: datetime
    planned_entry_price: float
    actual_entry_price: float | None
    entry_bar_index: int | None
    entry_time_utc: datetime | None
    stop_price: float
    target_price: float
    initial_risk: float
    exit_price: float | None
    exit_bar_index: int | None
    exit_time_utc: datetime | None
    exit_reason: str | None
    pnl: float | None
    pnl_in_r: float | None
    mfe_price: float | None
    mfe_in_r: float | None
    mae_price: float | None
    mae_in_r: float | None
    setup_notes: str | None
    reasons: list[str]
    created_at: datetime
    updated_at: datetime
