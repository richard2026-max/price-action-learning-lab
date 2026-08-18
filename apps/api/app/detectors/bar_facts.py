"""单K线事实 detector：bar_anatomy / doji / trend_bar / signal_bar_evidence。

对应 specs：bar-anatomy.md / doji.md / trend-bar.md / signal-bar-evidence.md。
全部只访问 ctx[0..i]（no lookahead by construction）。
"""

from __future__ import annotations

from collections.abc import Sequence

from app.detectors.base import DetectorMeta, DetectorOutput, register
from app.domain.bar import Bar
from app.structure.profile import params


def anatomy(ctx: Sequence[Bar], i: int) -> dict:
    """K线几何事实（spec: bar-anatomy.md）。比率字段在零波幅时为 None。"""
    b = ctx[i]
    rng = b.high - b.low
    body = abs(b.close - b.open)
    zero = rng == 0
    upper_tail = b.high - max(b.open, b.close)
    lower_tail = min(b.open, b.close) - b.low
    direction = "bull" if b.close > b.open else ("bear" if b.close < b.open else "neutral")
    facts: dict = {
        "direction": direction,
        "range": round(rng, 6),
        "body": round(body, 6),
        "body_ratio": None if zero else round(body / rng, 4),
        "upper_tail_ratio": None if zero else round(upper_tail / rng, 4),
        "lower_tail_ratio": None if zero else round(lower_tail / rng, 4),
        "close_location": None if zero else round((b.close - b.low) / rng, 4),
        "range_zero": zero,
        "relative_range": _relative_range(ctx, i),
    }
    return facts


def _relative_range(ctx: Sequence[Bar], i: int) -> float | None:
    """range / 此前 N 根的 range 均值（不含当前根；不足 N 根为 None）。"""
    n = int(params()["relative_range_window"])
    if i < n:
        return None
    window = ctx[i - n : i]
    avg = sum(b.high - b.low for b in window) / n
    rng = ctx[i].high - ctx[i].low
    if avg == 0:
        return None
    return round(rng / avg, 4)


def _is_inside(ctx: Sequence[Bar], i: int) -> bool | None:
    if i == 0:
        return None
    p, c = ctx[i - 1], ctx[i]
    return c.high <= p.high and c.low >= p.low


def _is_outside(ctx: Sequence[Bar], i: int) -> bool | None:
    if i == 0:
        return None
    p, c = ctx[i - 1], ctx[i]
    return c.high >= p.high and c.low <= p.low


def _is_doji(facts: dict) -> bool:
    if facts["range_zero"]:
        return True
    br = facts["body_ratio"]
    return br is not None and br <= params()["doji_body_ratio_max"]


def _mk(id_: str) -> DetectorMeta:
    return DetectorMeta(
        detector_id=id_,
        version="0.1.0",
        result_type="",
        label="",
        spec=f"docs/concepts/{id_.replace('_', '-')}.md",
        provenance="Mechanical Approximation",
    )


# ---------------- bar_anatomy ----------------
_meta_anatomy = DetectorMeta(
    detector_id="bar_anatomy", version="0.1.0", result_type="evidence_set",
    label="K线解剖事实", spec="docs/concepts/bar-anatomy.md",
    provenance="Mechanical Approximation",
)


def _fn_anatomy(ctx: Sequence[Bar], i: int) -> DetectorOutput:
    return DetectorOutput(result_type="evidence_set", result=anatomy(ctx, i), evidence={})


# ---------------- doji ----------------
_meta_doji = DetectorMeta(
    detector_id="doji", version="0.1.0", result_type="boolean",
    label="十字星候选", spec="docs/concepts/doji.md",
    provenance="Mechanical Approximation",
)


def _fn_doji(ctx: Sequence[Bar], i: int) -> DetectorOutput:
    facts = anatomy(ctx, i)
    return DetectorOutput(
        result_type="boolean",
        result=_is_doji(facts),
        evidence={"body_ratio": facts["body_ratio"], "range_zero": facts["range_zero"],
                  "threshold": params()["doji_body_ratio_max"]},
    )


# ---------------- trend_bar ----------------
_meta_trend = DetectorMeta(
    detector_id="trend_bar", version="0.1.0", result_type="categorical",
    label="趋势K线", spec="docs/concepts/trend-bar.md",
    provenance="Mechanical Approximation",
)


def _fn_trend(ctx: Sequence[Bar], i: int) -> DetectorOutput:
    facts = anatomy(ctx, i)
    doji = _is_doji(facts)
    if doji or facts["direction"] == "neutral":
        result = "none"
    else:
        result = f"{facts['direction']}_trend_bar"
    strong_body = params()["trend_bar_strong_body_ratio"]
    strong_rr = params()["trend_bar_strong_relative_range"]
    br, rr = facts["body_ratio"], facts["relative_range"]
    strong = None if (br is None or rr is None) else bool(br >= strong_body and rr >= strong_rr)
    if br is not None and rr is None and br >= strong_body:
        strong = None  # 历史不足时仅记录 body 条件，不判强
    return DetectorOutput(
        result_type="categorical",
        result=result,
        evidence={"body_ratio": br, "relative_range": rr, "strong": strong,
                  "strong_body_threshold": strong_body, "strong_rr_threshold": strong_rr},
    )


# ---------------- signal_bar_evidence ----------------
_meta_signal = DetectorMeta(
    detector_id="signal_bar_evidence", version="0.1.0", result_type="evidence_set",
    label="信号K线证据", spec="docs/concepts/signal-bar-evidence.md",
    provenance="Product / Engineering Design + Mechanical Approximation",
)


def _fn_signal(ctx: Sequence[Bar], i: int) -> DetectorOutput:
    facts = anatomy(ctx, i)
    up, lo = facts["upper_tail_ratio"], facts["lower_tail_ratio"]
    dominant = (
        "none" if up is None or lo is None or up == lo
        else ("upper" if up > lo else "lower")
    )
    evidence = {
        "direction": facts["direction"],
        "body_ratio": facts["body_ratio"],
        "upper_tail_ratio": up,
        "lower_tail_ratio": lo,
        "close_location": facts["close_location"],
        "dominant_tail": dominant,
        "relative_range": facts["relative_range"],
        "is_inside": _is_inside(ctx, i),
        "is_outside": _is_outside(ctx, i),
    }
    return DetectorOutput(result_type="evidence_set", result=evidence, evidence={})


def register_bar_facts() -> None:
    register(_meta_anatomy, _fn_anatomy)
    register(_meta_doji, _fn_doji)
    register(_meta_trend, _fn_trend)
    register(_meta_signal, _fn_signal)
