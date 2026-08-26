"""无前视的判断复盘上下文提取。

该服务以已提交的 ``JudgmentORM`` 为时间边界，而不是以当前 replay cursor
为边界。这样即使会话后来已经推进，也只能重建用户提交判断当时可见的训练日
K 线和 detector 候选；关联的模拟交易则作为明确标记的后验信息附带返回。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from app.domain.instrument import Instrument, get_instrument
from app.models.orm import JudgmentORM, SimTradeORM
from app.replay.service import ReplayError, ReplayService
from app.repositories.sim_trade_repo import SimTradeRepository
from app.services.detector_service import compute_candidates


@dataclass(frozen=True, slots=True)
class DecisionContext:
    """判断时刻的可序列化复盘上下文。"""

    session_id: str
    judgment_id: int
    day: str
    bar_index: int
    visible_bars: list[dict[str, Any]]
    ema20: list[float | None]
    key_levels: dict[str, Any]
    candidates: list[dict[str, Any]]
    judgment: dict[str, Any]
    sim_trades: list[dict[str, Any]] | None = None
    context_bars: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "judgment_id": self.judgment_id,
            "day": self.day,
            "bar_index": self.bar_index,
            # ``bars`` is the compact, backwards-friendly name used by callers.
            "bars": self.visible_bars,
            "visible_bars": self.visible_bars,
            "ema20": self.ema20,
            "key_levels": self.key_levels,
            "candidates": self.candidates,
            "judgment": self.judgment,
            "sim_trades": self.sim_trades,
            "context_bars": self.context_bars or [],
        }


class DecisionContextExtractor:
    """从 session + judgment 重建严格无前视的判断上下文。

    ``ReplayService`` 负责与现有行情加载逻辑保持一致；本服务只改变裁剪边界，
    使用 judgment.bar_index，而不使用 session.cursor_index。``max_visible_bars``
    默认 30，context bars 不计入该上限。
    """

    def __init__(
        self,
        replay_service: ReplayService,
        trade_repo: SimTradeRepository | None = None,
        *,
        max_visible_bars: int = 30,
        context_days: int = 0,
    ) -> None:
        if max_visible_bars < 1:
            raise ValueError("max_visible_bars must be positive")
        self._replay = replay_service
        self._trade_repo = trade_repo
        self._max_visible_bars = max_visible_bars
        self._context_days = max(0, context_days)

    def extract(
        self,
        session_id: str,
        judgment_id: int,
        instrument: Instrument | None = None,
    ) -> dict[str, Any]:
        """返回可直接 JSON 序列化的判断上下文。

        ``judgment_id`` 必须属于 ``session_id``。不存在的 session/judgment、越界
        bar_index 或不匹配的归属都会以 ReplayError 报告，避免静默拼接错误数据。
        """
        session = self._replay._repo.get(session_id)
        if session is None:
            raise ReplayError("not_found", "session 不存在", 404)

        judgment = self._find_judgment(session_id, judgment_id)
        if judgment is None:
            raise ReplayError("not_found", "judgment 不存在", 404)
        if judgment.session_id != session.id:
            raise ReplayError("invalid_judgment", "judgment 不属于该 session", 422)

        resolved = instrument or get_instrument(session.instrument_id, session.provider)
        data = self._replay._load(resolved, session.day, context_days=self._context_days)
        boundary = judgment.bar_index
        if boundary < 0 or boundary >= len(data.rth_bars):
            raise ReplayError("invalid_judgment", "judgment bar_index 超出训练日数据范围", 422)

        # This is the only training-day slice used below. Never use session.cursor_index.
        visible_all = data.rth_bars[: boundary + 1]
        first_visible = max(0, len(visible_all) - self._max_visible_bars)
        visible = visible_all[first_visible:]

        all_ema = self._replay._ema_for_all(data, boundary)
        context_count = len(data.context_bars)
        day_ema = all_ema[context_count:]
        ema = day_ema[first_visible:]
        candidates = compute_candidates(data.prev_day_rth, visible_all)

        context = DecisionContext(
            session_id=session.id,
            judgment_id=judgment.id,
            day=session.day.isoformat(),
            bar_index=boundary,
            visible_bars=[_bar_dict(b) for b in visible],
            ema20=ema,
            key_levels=_model_dict(self._replay._key_levels(data)),
            candidates=[_candidate_dict(c) for c in candidates],
            judgment=_orm_dict(judgment),
            sim_trades=(self._trades(session.id) if self._trade_repo is not None else None),
            context_bars=[_bar_dict(b) for b in data.context_bars],
        )
        return context.to_dict()

    # Explicit alias for callers that prefer a named context method.
    extract_context = extract

    def _find_judgment(self, session_id: str, judgment_id: int) -> JudgmentORM | None:
        # Repository currently exposes a session-scoped list, which is sufficient and
        # avoids changing its existing public API.
        return next(
            (j for j in self._replay._repo.list_judgments(session_id) if j.id == judgment_id),
            None,
        )

    def _trades(self, session_id: str) -> list[dict[str, Any]]:
        repo = self._trade_repo
        if repo is None:
            return []
        return [_orm_dict(t) for t in repo.list_trades_for_session(session_id)]


def _bar_dict(bar: Any) -> dict[str, Any]:
    return {
        "ts_open_utc": bar.ts_open_utc.isoformat(),
        "ts_close_utc": bar.ts_close_utc.isoformat(),
        "open": bar.open,
        "high": bar.high,
        "low": bar.low,
        "close": bar.close,
        "volume": bar.volume,
        "session": bar.session.value,
        "is_complete": bar.is_complete,
    }


def _candidate_dict(candidate: Any) -> dict[str, Any]:
    return {
        "detector_id": candidate.detector_id,
        "detector_version": candidate.detector_version,
        "bar_index": candidate.bar_index,
        "ts_event": candidate.ts_event.isoformat(),
        "ts_knowable": candidate.ts_knowable.isoformat(),
        "knowable_precision": candidate.knowable_precision,
        "result_type": candidate.result_type,
        "result": _json_value(candidate.result),
        "evidence": _json_value(candidate.evidence),
        "rule_source": candidate.rule_source,
        "provenance": candidate.provenance,
    }


def _model_dict(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return _json_value(model.model_dump(mode="json"))
    return _json_value({k: getattr(model, k) for k in model.__class__.__annotations__})


def _orm_dict(row: JudgmentORM | SimTradeORM) -> dict[str, Any]:
    return _json_value({column.name: getattr(row, column.name) for column in row.__table__.columns})


def _json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(v) for v in value]
    return value
