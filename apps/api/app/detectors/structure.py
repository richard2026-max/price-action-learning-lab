"""MVP-C 结构层 detector：swing / pullback_leg / hl_counting / trend_lines。

对应 specs：swing.md / pullback-leg.md / hl-counting.md / trend-lines.md。
关键语义：
- swing：需右侧 N=3 确认（knowable_at 晚于 event_at）；
- 结构上下文：优先利用当前已确认的 swing 序列（HL/LL/HH/LH）推导市场环境，回退至净漂移；
- hl_counting：状态机流式推进（H1..H4 / L1..L4），second_entry 标注；
- trend_lines：基于最近两个已确认的同向 swing 构造几何线，向右延伸探测触碰与突破。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.detectors.base import DetectorMeta, DetectorOutput, register
from app.domain.bar import Bar
from app.structure.profile import params

SWING_N = int(params()["swing_lookback"])  # pivot 强度（默认 3）
DRIFT_WINDOW = int(params()["context_drift_window"])  # 净漂移上下文窗口（默认 20）
MAX_COUNT = 4  # H4/L4 之后不再递增（Brooks 语义）


@dataclass(frozen=True, slots=True)
class ConfirmedSwing:
    kind: str  # "swing_high" | "swing_low"
    bar_index: int  # 极值K线下标
    price: float
    confirmed_at: int  # 确认发生的K线下标


def get_confirmed_swings(ctx: Sequence[Bar], up_to_index: int) -> list[ConfirmedSwing]:
    """收集截至 up_to_index 为止所有已确认的 swing（严格无前视）。"""
    swings: list[ConfirmedSwing] = []
    for k in range(SWING_N * 2, up_to_index + 1):
        res = _confirmed_swing(ctx, k)
        if res is not None:
            kind, j = res
            swings.append(ConfirmedSwing(
                kind=kind,
                bar_index=j,
                price=ctx[j].high if kind == "swing_high" else ctx[j].low,
                confirmed_at=k,
            ))
    return swings


# ---------------- 上下文方向（结合 Swing 序列与净漂移） ----------------
def _context_direction(ctx: Sequence[Bar], i: int) -> str:
    """推导当前K线的上下文方向。优先使用已确认 swing 序列结构，不足时使用收盘净漂移。"""
    swings = get_confirmed_swings(ctx, i)
    highs = [s for s in swings if s.kind == "swing_high"]
    lows = [s for s in swings if s.kind == "swing_low"]

    if len(highs) >= 2 and len(lows) >= 2:
        hh = highs[-1].price > highs[-2].price
        hl = lows[-1].price > lows[-2].price
        lh = highs[-1].price < highs[-2].price
        ll = lows[-1].price < lows[-2].price
        if hh and hl:
            return "up"
        if lh and ll:
            return "down"

    # 回退到收盘净漂移
    if i < DRIFT_WINDOW:
        return "flat"
    a, b = ctx[i - DRIFT_WINDOW].close, ctx[i].close
    if b > a:
        return "up"
    if b < a:
        return "down"
    return "flat"


# ---------------- swing（右侧确认型） ----------------
_meta_swing = DetectorMeta(
    detector_id="swing", version="0.1.0", result_type="categorical",
    label="摆动高低点", spec="docs/concepts/swing.md",
    provenance="Mechanical Approximation",
)


def _confirmed_swing(ctx: Sequence[Bar], i: int) -> tuple[str, int] | None:
    """在确认根 i 检查：i-N..i-1 是否全部更低高点/更高低点 → 确认 i-N 为 swing。"""
    j = i - SWING_N
    if j < SWING_N:
        return None
    # 检查左侧与右侧
    if all(ctx[k].high < ctx[j].high for k in range(j + 1, i + 1)):
        if all(ctx[k].high < ctx[j].high for k in range(j - SWING_N, j)):
            return "swing_high", j
    if all(ctx[k].low > ctx[j].low for k in range(j + 1, i + 1)):
        if all(ctx[k].low > ctx[j].low for k in range(j - SWING_N, j)):
            return "swing_low", j
    return None


def _fn_swing(ctx: Sequence[Bar], i: int) -> DetectorOutput | None:
    r = _confirmed_swing(ctx, i)
    if r is None:
        return None
    kind, j = r
    return DetectorOutput(
        result_type="categorical",
        result=kind,
        evidence={
            "swing_bar_index": j,
            "extreme": ctx[j].high if kind == "swing_high" else ctx[j].low,
            "lookback": SWING_N,
            "note": "knowable_at=确认根收盘，晚于极值根（右侧确认）",
        },
    )


# ---------------- pullback（单K线定义 + 结构上下文） ----------------
_meta_pullback = DetectorMeta(
    detector_id="pullback_leg", version="0.1.0", result_type="categorical",
    label="回调(bar pullback)", spec="docs/concepts/pullback-leg.md",
    provenance="Mechanical Approximation",
)


def _fn_pullback(ctx: Sequence[Bar], i: int) -> DetectorOutput | None:
    if i == 0:
        return None
    d = _context_direction(ctx, i)
    result = "none"
    if d == "up" and ctx[i].low < ctx[i - 1].low:
        result = "bull_pullback"
    elif d == "down" and ctx[i].high > ctx[i - 1].high:
        result = "bear_pullback"

    if result == "none":
        return DetectorOutput(
            result_type="categorical", result="none",
            evidence={"context": d, "note": "破前低/前高与上下文不符或未破"},
        )
    return DetectorOutput(
        result_type="categorical", result=result,
        evidence={"context": d, "prev_low": ctx[i - 1].low, "prev_high": ctx[i - 1].high},
    )


# ---------------- hl_counting（状态机事件） ----------------
_meta_hl = DetectorMeta(
    detector_id="hl_counting", version="0.1.0", result_type="categorical",
    label="H/L 计数", spec="docs/concepts/hl-counting.md",
    provenance="Mechanical Approximation",
)


class _HLState:
    """H/L 计数状态机（术语表定义直译）。service 层按会话 reset。"""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.h_count = 0
        self.l_count = 0
        self.saw_lower_high = True
        self.saw_higher_low = True
        self.last_direction = ""

    def step(self, ctx: Sequence[Bar], i: int) -> DetectorOutput | None:
        if i == 0:
            return None
        d = _context_direction(ctx, i)
        if d != self.last_direction and d in ("up", "down"):
            if self.last_direction and d != self.last_direction:
                self.reset()
            self.last_direction = d

        hh = ctx[i].high > ctx[i - 1].high
        lh = ctx[i].high < ctx[i - 1].high
        hl = ctx[i].low > ctx[i - 1].low
        ll = ctx[i].low < ctx[i - 1].low
        if lh:
            self.saw_lower_high = True
        if hl:
            self.saw_higher_low = True

        if d == "up" and hh and self.saw_lower_high and self.h_count < MAX_COUNT:
            self.h_count += 1
            self.saw_lower_high = False
            return DetectorOutput(
                result_type="categorical",
                result=f"H{self.h_count}",
                evidence={
                    "context": "up",
                    "second_entry": self.h_count == 2,
                    "higher_high": ctx[i].high,
                    "prev_high": ctx[i - 1].high,
                },
            )
        if d == "down" and ll and self.saw_higher_low and self.l_count < MAX_COUNT:
            self.l_count += 1
            self.saw_higher_low = False
            return DetectorOutput(
                result_type="categorical",
                result=f"L{self.l_count}",
                evidence={
                    "context": "down",
                    "second_entry": self.l_count == 2,
                    "lower_low": ctx[i].low,
                    "prev_low": ctx[i - 1].low,
                },
            )
        return None


HL_STATE = _HLState()


def _fn_hl(ctx: Sequence[Bar], i: int) -> DetectorOutput | None:
    return HL_STATE.step(ctx, i)


# ---------------- trend_lines（几何支撑阻力线） ----------------
_meta_trend_lines = DetectorMeta(
    detector_id="trend_lines", version="0.1.0", result_type="evidence_set",
    label="趋势线/通道线", spec="docs/concepts/trend-lines.md",
    provenance="Mechanical Approximation",
)


def _fn_trend_lines(ctx: Sequence[Bar], i: int) -> DetectorOutput | None:
    """基于当前已确认的 swing 序列构造趋势线并计算当前 bar 距离/突破。"""
    swings = get_confirmed_swings(ctx, i)
    highs = [s for s in swings if s.kind == "swing_high"]
    lows = [s for s in swings if s.kind == "swing_low"]

    bull_line: dict[str, object] | None = None
    bear_line: dict[str, object] | None = None

    # 多头趋势线（两点抬高的 swing_low 连线）
    if len(lows) >= 2:
        p1, p2 = lows[-2], lows[-1]
        dx = p2.bar_index - p1.bar_index
        if dx >= 3 and p2.price > p1.price:
            slope = (p2.price - p1.price) / dx
            line_val = p2.price + slope * (i - p2.bar_index)
            is_breakout = ctx[i].close < line_val
            bull_line = {
                "p1_index": p1.bar_index, "p1_price": p1.price,
                "p2_index": p2.bar_index, "p2_price": p2.price,
                "slope": round(slope, 4),
                "current_line_price": round(line_val, 4),
                "distance": round(ctx[i].close - line_val, 4),
                "breakout": is_breakout,
            }

    # 空头趋势线（两点降低的 swing_high 连线）
    if len(highs) >= 2:
        p1, p2 = highs[-2], highs[-1]
        dx = p2.bar_index - p1.bar_index
        if dx >= 3 and p2.price < p1.price:
            slope = (p2.price - p1.price) / dx
            line_val = p2.price + slope * (i - p2.bar_index)
            is_breakout = ctx[i].close > line_val
            bear_line = {
                "p1_index": p1.bar_index, "p1_price": p1.price,
                "p2_index": p2.bar_index, "p2_price": p2.price,
                "slope": round(slope, 4),
                "current_line_price": round(line_val, 4),
                "distance": round(ctx[i].close - line_val, 4),
                "breakout": is_breakout,
            }

    if bull_line is None and bear_line is None:
        return None

    return DetectorOutput(
        result_type="evidence_set",
        result={"bull_trend_line": bull_line, "bear_trend_line": bear_line},
        evidence={
            "total_swings_confirmed": len(swings),
            "has_bull_line": bull_line is not None,
            "has_bear_line": bear_line is not None,
        },
    )


def register_structure() -> None:
    register(_meta_swing, _fn_swing)
    register(_meta_pullback, _fn_pullback)
    register(_meta_hl, _fn_hl)
    register(_meta_trend_lines, _fn_trend_lines)
