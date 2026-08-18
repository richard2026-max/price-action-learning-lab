"""回放引擎（MVP-A 核心）。no lookahead by construction：

- 服务端持有全天K线，API 响应一律裁剪为 bars[0..cursor]；
- cursor 为服务端权威状态（SQLite），不信任客户端；
- EMA/关键价位只用"当时已知"数据计算（前日+盘前为已结束时段；EMA 以前日 RTH 收盘序列预热）；
- 判断（judgment）提交即锁定，bar_index 取服务端 cursor。
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime

from app.domain.bar import Bar, SessionType, Timeframe
from app.domain.instrument import Instrument
from app.repositories.replay_repo import ReplayRepository
from app.schemas.replay import (
    AdvanceIn,
    AnnotationIn,
    BarOut,
    CreateSessionIn,
    JudgmentIn,
    KeyLevelsOut,
    ReplayMode,
    SessionDetailOut,
    SessionInfoOut,
)
from app.services.calendar import XNYSCalendar
from app.services.market_data import MarketDataStore


class ReplayError(Exception):
    def __init__(self, code: str, message: str, status: int = 400) -> None:
        self.code, self.message, self.status = code, message, status


@dataclass(slots=True)
class _DayData:
    rth_bars: list[Bar]
    premarket_bars: list[Bar]
    prev_day_rth: list[Bar]
    session_close_utc: datetime | None


class ReplayService:
    def __init__(self, store: MarketDataStore, calendar: XNYSCalendar, repo: ReplayRepository) -> None:
        self._store = store
        self._cal = calendar
        self._repo = repo

    # ---------- 数据加载（服务端全量；不下发） ----------
    def _load(self, instrument: Instrument, day) -> _DayData:
        rth = self._store.read_day(instrument, Timeframe.M5, day, SessionType.RTH)
        if not rth:
            raise ReplayError("no_data", f"{day} 无 RTH 5m 数据（请先 seed/ingest）", 404)
        premarket = self._store.read_day(instrument, Timeframe.M5, day, SessionType.PREMARKET)
        prev_day = self._cal.prev_trading_day(day)
        prev_rth = self._store.read_day(instrument, Timeframe.M5, prev_day, SessionType.RTH)
        windows = self._cal.sessions_for(day)
        rth_close = next((w.end_utc for w in windows if w.session_type == "rth"), None)
        return _DayData(rth, premarket, prev_rth, rth_close)

    def available_days(self, instrument: Instrument, include_sealed: bool = False) -> list[str]:
        """获取可用交易日。默认自动排除封存考试日（避免训练污染）。"""
        from app.services.sealed_exam import partition_days

        datasets = self._store.list_datasets()
        all_days: set[str] = set()
        for m in datasets:
            if (
                m["provider"] == instrument.provider
                and m["instrument_id"] == instrument.instrument_id
                and m["timeframe"] == "5m"
            ):
                all_days.update(
                    b.ts_open_utc.date().isoformat()
                    for b in self._store.read_bars(
                        instrument, Timeframe.M5, _iso(m["start"][:10]), _iso(m["end"][:10])
                    )
                    if b.session == SessionType.RTH
                )
        if not all_days:
            return []
        training_days, sealed_days = partition_days(list(all_days))
        return sorted(all_days) if include_sealed else training_days

    def sealed_exam_days(self, instrument: Instrument) -> list[str]:
        """获取专属封存考试日列表（仅授权考试调用）。"""
        from app.services.sealed_exam import partition_days

        all_days = self.available_days(instrument, include_sealed=True)
        _, sealed = partition_days(all_days)
        return sealed

    def random_day(self, instrument: Instrument, seed: int, for_exam: bool = False) -> str:
        days = self.sealed_exam_days(instrument) if for_exam else self.available_days(instrument)
        if not days:
            raise ReplayError("no_data", "无可用数据", 404)
        return random.Random(seed).choice(days)

    # ---------- 会话 ----------
    def create(self, req: CreateSessionIn, instrument: Instrument) -> SessionDetailOut:
        from app.services.sealed_exam import is_sealed_exam_day

        day = _iso(req.day)
        if not self._cal.is_trading_day(day):
            raise ReplayError("not_trading_day", f"{req.day} 不是交易日", 422)

        # 封存集访问权限保护：普通回放模式禁止直接加载封存日
        is_sealed = is_sealed_exam_day(day)
        if is_sealed and req.mode != ReplayMode.EXAM:
            raise ReplayError(
                "sealed_exam_day_protected",
                f"{req.day} 为封存考试日，已被服务端严格隔离保护（防止读图前置污染）。"
                "如需评估盲测成绩，请以 mode='exam' 创建考试会话。",
                403,
            )

        data = self._load(instrument, day)
        if req.warmup_bars >= len(data.rth_bars):
            raise ReplayError("warmup_too_large", "warmup_bars 超过当日K线数", 422)
        orm = self._repo.create_session(
            instrument_id=instrument.instrument_id,
            provider=instrument.provider,
            day=day,
            timeframe=req.timeframe,
            mode=req.mode.value,
            warmup_bars=req.warmup_bars,
        )
        return self._detail(orm, data)

    def get(self, session_id: str, instrument: Instrument) -> SessionDetailOut:
        orm = self._repo.get(session_id)
        if orm is None:
            raise ReplayError("not_found", "session 不存在", 404)
        return self._detail(orm, self._load(instrument, orm.day))

    def advance(self, session_id: str, req: AdvanceIn, instrument: Instrument) -> SessionDetailOut:
        orm = self._repo.get(session_id)
        if orm is None:
            raise ReplayError("not_found", "session 不存在", 404)
        data = self._load(instrument, orm.day)
        last = len(data.rth_bars) - 1
        orm.cursor_index = min(orm.cursor_index + req.n, last)
        if orm.cursor_index >= last:
            orm.state = "completed"
        self._repo.update(orm)
        return self._detail(orm, data)

    def back(self, session_id: str, instrument: Instrument) -> SessionDetailOut:
        orm = self._repo.get(session_id)
        if orm is None:
            raise ReplayError("not_found", "session 不存在", 404)
        if orm.mode != "free":
            raise ReplayError("back_forbidden", "仅 free 模式允许回看上一根", 403)
        orm.cursor_index = max(orm.warmup_bars, orm.cursor_index - 1)
        orm.state = "running"
        self._repo.update(orm)
        return self._detail(orm, self._load(instrument, orm.day))

    # ---------- 判断与标注 ----------
    def submit_judgment(self, session_id: str, req: JudgmentIn, instrument: Instrument):
        orm = self._repo.get(session_id)
        if orm is None:
            raise ReplayError("not_found", "session 不存在", 404)
        data = self._load(instrument, orm.day)
        cursor_bar = data.rth_bars[orm.cursor_index]
        j = self._repo.add_judgment(
            session_id=orm.id, bar_index=orm.cursor_index, bar_time_utc=cursor_bar.ts_close_utc,
            payload=req.model_dump(mode="json"),
        )
        return j

    def add_annotation(self, session_id: str, req: AnnotationIn, instrument: Instrument):
        orm = self._repo.get(session_id)
        if orm is None:
            raise ReplayError("not_found", "session 不存在", 404)
        data = self._load(instrument, orm.day)
        if req.bar_index > orm.cursor_index:
            raise ReplayError("future_bar", "不能标注 cursor 之后的K线", 403)
        bar = data.rth_bars[req.bar_index]
        return self._repo.add_annotation(
            orm.id, req.bar_index, bar.ts_close_utc, req.kind, req.label, req.text
        )

    # ---------- 视图组装（唯一出口：bars 一律裁剪到 cursor） ----------
    def _detail(self, orm, data: _DayData) -> SessionDetailOut:
        from app.schemas.replay import CandidateOut
        from app.services.detector_service import compute_candidates

        visible = data.rth_bars[: orm.cursor_index + 1]
        key_levels = self._key_levels(data)
        ema = self._ema20_visible(data, orm.cursor_index)
        bar = data.rth_bars[orm.cursor_index]
        # Predict First：会话存在已提交判断才解锁系统候选（先判断后揭晓）
        candidates: list[CandidateOut] = []
        if self._repo.list_judgments(orm.id):
            candidates = [
                CandidateOut(
                    detector_id=c.detector_id, detector_version=c.detector_version,
                    bar_index=c.bar_index, ts_event=c.ts_event, ts_knowable=c.ts_knowable,
                    knowable_precision=c.knowable_precision, result_type=c.result_type,
                    result=c.result, evidence=c.evidence, rule_source=c.rule_source,
                    provenance=c.provenance,
                )
                for c in compute_candidates(data.prev_day_rth, visible)
            ]
        return SessionDetailOut(
            session_id=orm.id,
            bars=[
                BarOut(
                    ts_open_utc=b.ts_open_utc,
                    ts_close_utc=b.ts_close_utc,
                    open=b.open, high=b.high, low=b.low, close=b.close,
                    volume=b.volume, session=b.session.value, is_complete=b.is_complete,
                )
                for b in visible
            ],
            ema20=ema,
            key_levels=key_levels,
            info=SessionInfoOut(
                day=orm.day.isoformat(),
                provider=orm.provider,
                session_name="rth",
                bar_index=orm.cursor_index,
                market_time_utc=bar.ts_close_utc,
                session_close_utc=data.session_close_utc,
                is_completed=orm.state == "completed",
                mode=orm.mode,
                sampling_mode=orm.sampling_mode,
            ),
            candidates=candidates,
        )

    @staticmethod
    def _key_levels(data: _DayData) -> KeyLevelsOut:
        prev_h = max((b.high for b in data.prev_day_rth), default=None)
        prev_l = min((b.low for b in data.prev_day_rth), default=None)
        prev_c = data.prev_day_rth[-1].close if data.prev_day_rth else None
        today_open = data.rth_bars[0].open if data.rth_bars else None
        pre_h = max((b.high for b in data.premarket_bars), default=None)
        pre_l = min((b.low for b in data.premarket_bars), default=None)
        gap = round(today_open - prev_c, 4) if (today_open is not None and prev_c is not None) else None
        return KeyLevelsOut(
            prev_day_high=prev_h, prev_day_low=prev_l, prev_day_close=prev_c,
            today_open=today_open, premarket_high=pre_h, premarket_low=pre_l, gap=gap,
        )

    @staticmethod
    def _ema20_visible(data: _DayData, cursor_index: int) -> list[float | None]:
        """EMA20：以前一交易日 RTH 收盘序列预热（已结束时段，无前视），再迭代当日可见K线。
        前日数据不足 20 根时，早期值返回 None（不伪造有效 EMA）。"""
        k = 2.0 / 21.0
        warmup_closes = [b.close for b in data.prev_day_rth]
        visible_closes = [b.close for b in data.rth_bars[: cursor_index + 1]]

        out: list[float | None] = []
        ema: float | None = None
        if len(warmup_closes) >= 20:
            ema = sum(warmup_closes[:20]) / 20.0
            for c in warmup_closes[20:]:
                ema = c * k + ema * (1 - k)

        for i, c in enumerate(visible_closes):
            if ema is None:
                window = warmup_closes + visible_closes[: i + 1]
                if len(window) >= 20:
                    ema = sum(window[:20]) / 20.0
                    for w in window[20:]:
                        ema = w * k + ema * (1 - k)
                    out.append(round(ema, 4))
                else:
                    out.append(None)
            else:
                ema = c * k + ema * (1 - k)
                out.append(round(ema, 4))
        return out


def _iso(s: str):
    from datetime import date as _d

    return _d.fromisoformat(s)
