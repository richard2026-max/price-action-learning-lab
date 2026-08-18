"""Level 5 复杂 Brooks 形态识别器：wedge / climax / micro_channel。

对应 specs：docs/concepts/wedge.md, climax.md, micro-channel.md。
全部基于确认的 Swing、K线解剖事实与均线/通道几何，严格无前视。
"""

from __future__ import annotations

from collections.abc import Sequence

from app.detectors.bar_facts import anatomy
from app.detectors.base import DetectorMeta, DetectorOutput, register
from app.detectors.structure import get_confirmed_swings
from app.domain.bar import Bar
from app.structure.profile import params

# ---------------- 1. wedge (楔形三推) ----------------
_meta_wedge = DetectorMeta(
    detector_id="wedge",
    version="0.1.0",
    result_type="categorical",
    label="楔形/三推形态",
    spec="docs/concepts/wedge.md",
    provenance="Mechanical Approximation",
)


def _fn_wedge(ctx: Sequence[Bar], i: int) -> DetectorOutput | None:
    swings = get_confirmed_swings(ctx, i)
    highs = [s for s in swings if s.kind == "swing_high"]
    lows = [s for s in swings if s.kind == "swing_low"]

    # 上升楔形（Rising Wedge / 3 pushes up）：连续 3 个递增高点 + 推进衰减
    if len(highs) >= 3:
        h1, h2, h3 = highs[-3], highs[-2], highs[-1]
        if h1.price < h2.price < h3.price:
            push1 = h2.price - h1.price
            push2 = h3.price - h2.price
            # 必须最近刚刚确认第三推（h3.confirmed_at 接近当前 i）
            if i - h3.confirmed_at <= 2 and push2 <= push1 * 1.1:
                return DetectorOutput(
                    result_type="categorical",
                    result="rising_wedge",
                    evidence={
                        "pushes": [h1.price, h2.price, h3.price],
                        "push1_gain": round(push1, 4),
                        "push2_gain": round(push2, 4),
                        "h3_index": h3.bar_index,
                        "decay_ratio": round(push2 / push1, 4) if push1 > 0 else None,
                    },
                )

    # 下降楔形（Falling Wedge / 3 pushes down）：连续 3 个递减低点 + 推进衰减
    if len(lows) >= 3:
        l1, l2, l3 = lows[-3], lows[-2], lows[-1]
        if l1.price > l2.price > l3.price:
            drop1 = l1.price - l2.price
            drop2 = l2.price - l3.price
            if i - l3.confirmed_at <= 2 and drop2 <= drop1 * 1.1:
                return DetectorOutput(
                    result_type="categorical",
                    result="falling_wedge",
                    evidence={
                        "pushes": [l1.price, l2.price, l3.price],
                        "drop1_gain": round(drop1, 4),
                        "drop2_gain": round(drop2, 4),
                        "l3_index": l3.bar_index,
                        "decay_ratio": round(drop2 / drop1, 4) if drop1 > 0 else None,
                    },
                )

    return None


# ---------------- 2. climax (高潮反转) ----------------
_meta_climax = DetectorMeta(
    detector_id="climax",
    version="0.1.0",
    result_type="categorical",
    label="高潮形态",
    spec="docs/concepts/climax.md",
    provenance="Mechanical Approximation",
)


def _fn_climax(ctx: Sequence[Bar], i: int) -> DetectorOutput | None:
    if i < 3:
        return None

    facts_cur = anatomy(ctx, i)
    rr = facts_cur["relative_range"]

    # 1. 极致单K线高潮 (Single Exhaustion Bar)
    if rr is not None and rr >= 2.6 and facts_cur["body_ratio"] is not None and facts_cur["body_ratio"] >= 0.7:
        res = "buy_climax" if facts_cur["direction"] == "bull" else "sell_climax"
        return DetectorOutput(
            result_type="categorical",
            result=res,
            evidence={
                "type": "single_exhaustion_bar",
                "relative_range": rr,
                "body_ratio": facts_cur["body_ratio"],
            },
        )

    # 2. 连续 3 根强趋势K线加速高潮 (Consecutive Trend Bars Climax)
    facts_prev1 = anatomy(ctx, i - 1)
    facts_prev2 = anatomy(ctx, i - 2)

    all_bull = (
        facts_cur["direction"] == "bull"
        and facts_prev1["direction"] == "bull"
        and facts_prev2["direction"] == "bull"
    )
    all_bear = (
        facts_cur["direction"] == "bear"
        and facts_prev1["direction"] == "bear"
        and facts_prev2["direction"] == "bear"
    )

    if all_bull or all_bear:
        b1, b2, b3 = facts_prev2["body_ratio"], facts_prev1["body_ratio"], facts_cur["body_ratio"]
        if b1 and b2 and b3 and b1 >= 0.55 and b2 >= 0.55 and b3 >= 0.55:
            # 检查总涨跌幅
            total_span = abs(ctx[i].close - ctx[i - 2].open)
            avg_rng = sum(ctx[k].high - ctx[k].low for k in range(max(0, i - 20), i)) / max(1, min(i, 20))
            if avg_rng > 0 and total_span >= avg_rng * 2.8:
                return DetectorOutput(
                    result_type="categorical",
                    result="buy_climax" if all_bull else "sell_climax",
                    evidence={
                        "type": "consecutive_trend_bars",
                        "total_span": round(total_span, 4),
                        "span_multiple_of_atr": round(total_span / avg_rng, 2),
                    },
                )

    return None


# ---------------- 3. micro_channel (微型通道) ----------------
_meta_micro_channel = DetectorMeta(
    detector_id="micro_channel",
    version="0.1.0",
    result_type="categorical",
    label="微型通道",
    spec="docs/concepts/micro-channel.md",
    provenance="Mechanical Approximation",
)


def _fn_micro_channel(ctx: Sequence[Bar], i: int) -> DetectorOutput | None:
    min_len = int(params().get("micro_channel_min_bars", 4))
    if i < min_len - 1:
        return None

    # 多头微型通道：向前扫描连续 low[k] >= low[k-1]
    bull_len = 1
    for k in range(i, 0, -1):
        if ctx[k].low >= ctx[k - 1].low:
            bull_len += 1
        else:
            break

    if bull_len >= min_len:
        return DetectorOutput(
            result_type="categorical",
            result="bull_micro_channel",
            evidence={
                "channel_length": bull_len,
                "first_bar_index": i - bull_len + 1,
                "lowest_low": min(b.low for b in ctx[i - bull_len + 1 : i + 1]),
            },
        )

    # 空头微型通道：向前扫描连续 high[k] <= high[k-1]
    bear_len = 1
    for k in range(i, 0, -1):
        if ctx[k].high <= ctx[k - 1].high:
            bear_len += 1
        else:
            break

    if bear_len >= min_len:
        return DetectorOutput(
            result_type="categorical",
            result="bear_micro_channel",
            evidence={
                "channel_length": bear_len,
                "first_bar_index": i - bear_len + 1,
                "highest_high": max(b.high for b in ctx[i - bear_len + 1 : i + 1]),
            },
        )

    return None


def register_complex() -> None:
    register(_meta_wedge, _fn_wedge)
    register(_meta_climax, _fn_climax)
    register(_meta_micro_channel, _fn_micro_channel)
