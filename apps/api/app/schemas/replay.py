"""回放相关 Pydantic schema。

Predict First 十问（PRD §2.2）：环境/方向/结构/回调/bar counting/是否交易/方向/两个理由/入场止损目标/概率自估。
概率与置信使用档位（good/okay/bad），禁 0-100 伪精确分（brooks-system-design-implications §一.3）。
止损语义 = 失效点（invalidation），非"市场最坏预测位"。
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReplayMode(StrEnum):
    FREE = "free"
    HIDDEN_ANSWER = "hidden_answer"
    EXAM = "exam"  # 封存考试模式：专用于抽取封存集进行盲测评估，严格禁止回看与前视


class ContextLabel(StrEnum):
    TREND_UP = "trend_up"
    TREND_DOWN = "trend_down"
    TRADING_RANGE = "trading_range"
    TRANSITION = "transition"


class Direction(StrEnum):
    LONG = "long"
    SHORT = "short"
    NONE = "none"


class Grade(StrEnum):
    """主观概率/置信档位（Brooks: good / okay / bad）。"""

    GOOD = "good"
    OKAY = "okay"
    BAD = "bad"


class Ternary(StrEnum):
    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


class CreateSessionIn(BaseModel):
    instrument_id: str = "SPY"
    provider: str = "synthetic"
    day: str = Field(..., description="交易日 YYYY-MM-DD（交易所本地日）")
    timeframe: str = "5m"
    mode: ReplayMode = ReplayMode.FREE
    warmup_bars: int = Field(6, ge=0, le=100)


class BarOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    ts_open_utc: datetime
    ts_close_utc: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    session: str
    is_complete: bool


class KeyLevelsOut(BaseModel):
    """日线关键价位覆盖层。仅使用已结束交易时段的数据（防前视）。"""

    prev_day_high: float | None = None
    prev_day_low: float | None = None
    prev_day_close: float | None = None
    today_open: float | None = None
    premarket_high: float | None = None
    premarket_low: float | None = None
    gap: float | None = None  # today_open - prev_day_close


class SessionInfoOut(BaseModel):
    """显示现实中已知时间信息——隐藏未来价格，不模拟失忆。"""

    day: str
    provider: str = "synthetic"
    session_name: str = "rth"
    bar_index: int
    market_time_utc: datetime  # 当前 cursor bar 收盘时刻
    session_close_utc: datetime | None = None
    is_completed: bool
    mode: str
    sampling_mode: str


class CandidateOut(BaseModel):
    """detector 候选（MVP-B 客观价格事实）。仅当会话已有判断（Predict First 解锁）才下发。"""

    detector_id: str
    detector_version: str
    bar_index: int
    ts_event: datetime
    ts_knowable: datetime
    knowable_precision: str
    result_type: str
    result: object
    evidence: dict
    rule_source: str
    provenance: str


class SessionDetailOut(BaseModel):
    session_id: str
    bars: list[BarOut]  # 仅包含 ts_close_utc <= cursor bar 的K线（服务端权威裁剪）
    ema20: list[float | None]  # 与 bars 等长；由前日已收盘数据预热（无前视），预热不足时早期为 None
    key_levels: KeyLevelsOut
    info: SessionInfoOut
    candidates: list[CandidateOut] = []  # 未解锁时为空列表


class AdvanceIn(BaseModel):
    n: int = Field(1, ge=1, le=50)


class JudgmentIn(BaseModel):
    """Predict First 判断表单（提交后锁定）。"""

    context_label: ContextLabel
    structure_note: str = ""
    pullback_present: Ternary = Ternary.UNKNOWN
    bar_counting_note: str = ""
    considering_trade: bool = False
    direction: Direction = Direction.NONE
    reasons: list[str] = Field(default_factory=list)
    entry: float | None = None
    stop: float | None = None  # 失效点：我承认判断错误的位置
    target: float | None = None
    probability_estimate: Grade = Grade.OKAY
    confidence: Grade = Grade.OKAY

    @model_validator(mode="after")
    def _validate_trade_plan(self) -> JudgmentIn:
        if self.considering_trade:
            if self.direction == Direction.NONE:
                raise ValueError("considering_trade=true 时 direction 不能为 none")
            if len([r for r in self.reasons if r.strip()]) < 2:
                raise ValueError("至少写出两个理由（two reasons to take a trade）")
            if self.entry is None or self.stop is None or self.target is None:
                raise ValueError("考虑交易时必须填写 entry / stop / target")
            if self.direction == Direction.LONG:
                if not (self.stop < self.entry < self.target):
                    raise ValueError("做多要求 stop < entry < target（stop 是失效点，不是预测位）")
            else:
                if not (self.target < self.entry < self.stop):
                    raise ValueError("做空要求 target < entry < stop（stop 是失效点，不是预测位）")
        return self


class JudgmentOut(BaseModel):
    id: int
    session_id: str
    bar_index: int
    bar_time_utc: datetime
    payload: dict
    submitted_at: datetime


class AnnotationIn(BaseModel):
    bar_index: int = Field(..., ge=0)
    kind: str = Field("note", pattern="^(label|note)$")
    label: str | None = Field(None, max_length=64)
    text: str | None = Field(None, max_length=4000)


class AnnotationOut(BaseModel):
    id: int
    session_id: str
    bar_index: int
    bar_time_utc: datetime
    kind: str
    label: str | None
    text: str | None
    created_at: datetime
    updated_at: datetime
