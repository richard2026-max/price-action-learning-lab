"""双K线/序列模式 detector：inside_bar / outside_bar / bar_pattern(ii·iii·ioi)。

对应 specs：inside-bar.md / outside-bar.md / ii-iii-ioi.md。
含等于语义（tie_policy=inclusive，与原书"或等于"一致）。
"""

from __future__ import annotations

from collections.abc import Sequence

from app.detectors.base import DetectorMeta, DetectorOutput, register
from app.domain.bar import Bar


def is_inside(ctx: Sequence[Bar], i: int) -> bool | None:
    if i == 0:
        return None
    p, c = ctx[i - 1], ctx[i]
    return bool(c.high <= p.high and c.low >= p.low)


def is_outside(ctx: Sequence[Bar], i: int) -> bool | None:
    if i == 0:
        return None
    p, c = ctx[i - 1], ctx[i]
    return bool(c.high >= p.high and c.low <= p.low)


# ---------------- inside_bar ----------------
_meta_inside = DetectorMeta(
    detector_id="inside_bar", version="0.1.0", result_type="boolean",
    label="内包线", spec="docs/concepts/inside-bar.md",
    provenance="Mechanical Approximation",
)


def _fn_inside(ctx: Sequence[Bar], i: int) -> DetectorOutput | None:
    r = is_inside(ctx, i)
    if r is None:
        return None  # 首根无前验：不判定（spec：首根K线不判定）
    return DetectorOutput(
        result_type="boolean",
        result=r,
        evidence={
            "prev_high": ctx[i - 1].high, "prev_low": ctx[i - 1].low,
            "high": ctx[i].high, "low": ctx[i].low, "tie_policy": "inclusive",
        },
    )


# ---------------- outside_bar ----------------
_meta_outside = DetectorMeta(
    detector_id="outside_bar", version="0.1.0", result_type="boolean",
    label="外包线", spec="docs/concepts/outside-bar.md",
    provenance="Mechanical Approximation",
)


def _fn_outside(ctx: Sequence[Bar], i: int) -> DetectorOutput | None:
    r = is_outside(ctx, i)
    if r is None:
        return None  # 首根无前验：不判定
    direction = (
        "outside_up" if ctx[i].close > ctx[i].open
        else ("outside_down" if ctx[i].close < ctx[i].open else "neutral")
    )
    return DetectorOutput(
        result_type="boolean",
        result=r,
        evidence={
            "prev_high": ctx[i - 1].high, "prev_low": ctx[i - 1].low,
            "high": ctx[i].high, "low": ctx[i].low,
            "direction": direction, "tie_policy": "inclusive",
        },
    )


# ---------------- bar_pattern（ii / iii / ioi）----------------
_meta_pattern = DetectorMeta(
    detector_id="bar_pattern", version="0.1.0", result_type="categorical",
    label="ii/iii/ioi 序列", spec="docs/concepts/ii-iii-ioi.md",
    provenance="Mechanical Approximation",
)


def _fn_pattern(ctx: Sequence[Bar], i: int) -> DetectorOutput | None:
    if i < 1:
        return None
    ins_i = is_inside(ctx, i)
    if not ins_i:
        return None
    result: str | None = None
    evidence: dict = {"bars": [i - 1, i], "tie_policy": "inclusive"}

    if i >= 2 and is_inside(ctx, i - 1):
        result = "ii"
        evidence["bars"] = [i - 2, i - 1, i]
        if i >= 3 and is_inside(ctx, i - 2):
            result = "iii"
            evidence["bars"] = [i - 3, i - 2, i - 1, i]
    if result is None and i >= 2 and is_outside(ctx, i - 1) and is_inside(ctx, i - 2):
        result = "ioi"
        evidence["bars"] = [i - 2, i - 1, i]
    if result is None:
        return None
    return DetectorOutput(result_type="categorical", result=result, evidence=evidence)


def register_patterns() -> None:
    register(_meta_inside, _fn_inside)
    register(_meta_outside, _fn_outside)
    register(_meta_pattern, _fn_pattern)
