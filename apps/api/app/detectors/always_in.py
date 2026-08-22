"""Always In 方向状态机 detector（Level 4 市场环境核心，Brooks Source）。

对应 spec：docs/concepts/always-in.md。
基于已确认 Swing 序列与 H/L 计数状态机组合判定 always-in long / short / transition。
仅翻转时发出事件（连续同向不重复），transition 不视为独立方向。
"""

from __future__ import annotations

from collections.abc import Sequence

from app.detectors.base import DetectorMeta, DetectorOutput, register
from app.detectors.structure import HL_STATE
from app.domain.bar import Bar


class _AlwaysInState:
    """Always In 状态机（service 层按会话 reset）。"""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.current: str = "transition"

    def step(self, ctx: Sequence[Bar], i: int, hl_state: object) -> str:
        """在 bar i 收盘时计算当前 always-in 状态。返回 "long"/"short"/"transition"。"""
        from app.detectors.structure import get_confirmed_swings

        # 1. 基于 H/L 计数（H3/H4 → long，L3/L4 → short）
        h_cnt = getattr(hl_state, "h_count", 0)
        l_cnt = getattr(hl_state, "l_count", 0)

        if h_cnt >= 3:
            return "long"
        if l_cnt >= 3:
            return "short"

        # 2. 基于已确认 swing 序列结构（HH+HL / LH+LL）
        swings = get_confirmed_swings(ctx, i)
        highs = [s for s in swings if s.kind == "swing_high"]
        lows = [s for s in swings if s.kind == "swing_low"]

        if len(highs) >= 2 and len(lows) >= 2:
            hh = highs[-1].price > highs[-2].price
            hl_ok = lows[-1].price > lows[-2].price
            lh = highs[-1].price < highs[-2].price
            ll = lows[-1].price < lows[-2].price

            if hh and hl_ok:
                return "long"
            if lh and ll:
                return "short"

        # 3. 无明确结构信号 → 维持上次状态（Brooks：状态不轻易翻转）
        return self.current


_meta_always_in = DetectorMeta(
    detector_id="always_in",
    version="0.1.0",
    result_type="categorical",
    label="Always In 方向",
    spec="docs/concepts/always-in.md",
    provenance="Mechanical Approximation",
)

AI_STATE = _AlwaysInState()


def _fn_always_in(ctx: Sequence[Bar], i: int) -> DetectorOutput | None:
    new_state = AI_STATE.step(ctx, i, HL_STATE)
    old_state = AI_STATE.current
    AI_STATE.current = new_state

    # 仅翻转时发出事件（event 型 detector）
    if new_state == old_state:
        return None

    label = f"always_in_{new_state}" if new_state != "transition" else "transition"
    prev_label = f"always_in_{old_state}" if old_state != "transition" else "transition"
    return DetectorOutput(
        result_type="categorical",
        result=label,
        evidence={"previous": prev_label, "current": new_state, "flip": True},
    )


def register_always_in() -> None:
    register(_meta_always_in, _fn_always_in)
