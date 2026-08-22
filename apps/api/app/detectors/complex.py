"""Level 3-5 Brooks 形态识别器：wedge / climax / micro_channel / breakout / double_top_bottom。

对应 specs：docs/concepts/wedge.md, climax.md, micro-channel.md, breakout.md, double-top-bottom.md。
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

    if len(highs) >= 3:
        h1, h2, h3 = highs[-3], highs[-2], highs[-1]
        if h1.price < h2.price < h3.price:
            push1 = h2.price - h1.price
            push2 = h3.price - h2.price
            if i - h3.confirmed_at <= 2 and push2 <= push1 * 1.1 and push1 > 0:
                return DetectorOutput(
                    result_type="categorical", result="rising_wedge",
                    evidence={"pushes": [h1.price, h2.price, h3.price],
                              "push1_gain": round(push1, 4), "push2_gain": round(push2, 4),
                              "h3_index": h3.bar_index,
                              "decay_ratio": round(push2 / push1, 4)},
                )

    if len(lows) >= 3:
        l1, l2, l3 = lows[-3], lows[-2], lows[-1]
        if l1.price > l2.price > l3.price:
            drop1 = l1.price - l2.price
            drop2 = l2.price - l3.price
            if i - l3.confirmed_at <= 2 and drop2 <= drop1 * 1.1 and drop1 > 0:
                return DetectorOutput(
                    result_type="categorical", result="falling_wedge",
                    evidence={"pushes": [l1.price, l2.price, l3.price],
                              "drop1_gain": round(drop1, 4), "drop2_gain": round(drop2, 4),
                              "l3_index": l3.bar_index,
                              "decay_ratio": round(drop2 / drop1, 4)},
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

    # 极致单K线衰竭
    if rr is not None and rr >= float(params().get("climax_exhaustion_relative_range", 2.6)):
        br = facts_cur["body_ratio"]
        if br is not None and br >= 0.7:
            res = "buy_climax" if facts_cur["direction"] == "bull" else "sell_climax"
            return DetectorOutput(
                result_type="categorical", result=res,
                evidence={"type": "single_exhaustion_bar", "relative_range": rr, "body_ratio": br},
            )

    # 连续趋势棒加速
    facts_p1 = anatomy(ctx, i - 1)
    facts_p2 = anatomy(ctx, i - 2)
    cur_dir, p1_dir, p2_dir = facts_cur["direction"], facts_p1["direction"], facts_p2["direction"]
    all_bull = cur_dir == "bull" == p1_dir == p2_dir
    all_bear = cur_dir == "bear" == p1_dir == p2_dir

    if all_bull or all_bear:
        b1, b2, b3 = facts_p2["body_ratio"], facts_p1["body_ratio"], facts_cur["body_ratio"]
        if b1 and b2 and b3 and b1 >= 0.55 and b2 >= 0.55 and b3 >= 0.55:
            total_span = abs(ctx[i].close - ctx[i - 2].open)
            lookback = min(i, int(params()["relative_range_window"]))
            avg_rng = sum(ctx[k].high - ctx[k].low for k in range(max(0, i - lookback), i)) / max(1, lookback)
            threshold = float(params().get("climax_consecutive_atr_span", 2.8))
            if avg_rng > 0 and total_span >= avg_rng * threshold:
                return DetectorOutput(
                    result_type="categorical",
                    result="buy_climax" if all_bull else "sell_climax",
                    evidence={"type": "consecutive_trend_bars",
                              "total_span": round(total_span, 4),
                              "span_multiple_of_atr": round(total_span / avg_rng, 2)},
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

    bull_len = 1
    for k in range(i, 0, -1):
        if ctx[k].low >= ctx[k - 1].low:
            bull_len += 1
        else:
            break

    if bull_len >= min_len:
        return DetectorOutput(
            result_type="categorical", result="bull_micro_channel",
            evidence={"channel_length": bull_len,
                      "first_bar_index": i - bull_len + 1,
                      "lowest_low": min(b.low for b in ctx[i - bull_len + 1 : i + 1])},
        )

    bear_len = 1
    for k in range(i, 0, -1):
        if ctx[k].high <= ctx[k - 1].high:
            bear_len += 1
        else:
            break

    if bear_len >= min_len:
        return DetectorOutput(
            result_type="categorical", result="bear_micro_channel",
            evidence={"channel_length": bear_len,
                      "first_bar_index": i - bear_len + 1,
                      "highest_high": max(b.high for b in ctx[i - bear_len + 1 : i + 1])},
        )
    return None


# ---------------- 4. breakout (突破与失败突破) ----------------
_meta_breakout = DetectorMeta(
    detector_id="breakout",
    version="0.1.0",
    result_type="categorical",
    label="突破/失败突破",
    spec="docs/concepts/breakout.md",
    provenance="Mechanical Approximation",
)

# 运行时状态：跟踪最近一次 breakout 事件
_breakout_state: dict = {"last_event_bar": -1, "last_direction": "", "last_swing_price": 0.0}
FAILED_WINDOW = 3


def _fn_breakout(ctx: Sequence[Bar], i: int) -> DetectorOutput | None:
    global _breakout_state
    if i == 0:
        return None

    swings = get_confirmed_swings(ctx, i)
    highs = [s for s in swings if s.kind == "swing_high"]
    lows = [s for s in swings if s.kind == "swing_low"]

    close = ctx[i].close
    prev_close = ctx[i - 1].close

    # 检测新突破
    if highs:
        last_sh = highs[-1]
        if close > last_sh.price and prev_close <= last_sh.price:
            _breakout_state["last_event_bar"] = i
            _breakout_state["last_direction"] = "bull"
            _breakout_state["last_swing_price"] = last_sh.price
            return DetectorOutput(
                result_type="categorical", result="bull_breakout",
                evidence={"breakout_level": last_sh.price, "close": close},
            )
    if lows:
        last_sl = lows[-1]
        if close < last_sl.price and prev_close >= last_sl.price:
            _breakout_state["last_event_bar"] = i
            _breakout_state["last_direction"] = "bear"
            _breakout_state["last_swing_price"] = last_sl.price
            return DetectorOutput(
                result_type="categorical", result="bear_breakout",
                evidence={"breakout_level": last_sl.price, "close": close},
            )

    # 检测 failed breakout（在 FAILED_WINDOW 根内回穿）
    eb = _breakout_state.get("last_event_bar", -1)
    edir = _breakout_state.get("last_direction", "")
    elevel = _breakout_state.get("last_swing_price", 0.0)
    if eb > 0 and 0 < i - eb <= FAILED_WINDOW and edir:
        if edir == "bull" and close < elevel:
            _breakout_state["last_event_bar"] = -1
            return DetectorOutput(
                result_type="categorical", result="failed_bull_breakout",
                evidence={"breakout_level": elevel, "close_back_below": close,
                          "bars_since_breakout": i - eb},
            )
        if edir == "bear" and close > elevel:
            _breakout_state["last_event_bar"] = -1
            return DetectorOutput(
                result_type="categorical", result="failed_bear_breakout",
                evidence={"breakout_level": elevel, "close_back_above": close,
                          "bars_since_breakout": i - eb},
            )
    return None


# ---------------- 5. double_top_bottom (双顶双底) ----------------
_meta_double = DetectorMeta(
    detector_id="double_top_bottom",
    version="0.1.0",
    result_type="categorical",
    label="双顶/双底",
    spec="docs/concepts/double-top-bottom.md",
    provenance="Mechanical Approximation",
)


def _fn_double(ctx: Sequence[Bar], i: int) -> DetectorOutput | None:
    swings = get_confirmed_swings(ctx, i)
    highs = [s for s in swings if s.kind == "swing_high"]
    lows = [s for s in swings if s.kind == "swing_low"]

    # 计算容差（近20根均幅的25%）
    if i < 1:
        return None
    lookback = min(i, int(params()["relative_range_window"]))
    if lookback <= 0:
        return None
    avg_rng = sum(ctx[k].high - ctx[k].low for k in range(max(0, i - lookback), i)) / max(1, lookback)
    if avg_rng <= 0:
        return None
    tolerance = avg_rng * float(params().get("double_tolerance_ratio", 0.25))

    # double_bottom：最近两个 swing_low 价差 ≤ tolerance，间隔 ≥3
    if len(lows) >= 2:
        l1, l2 = lows[-2], lows[-1]
        gap = l2.bar_index - l1.bar_index
        diff = abs(l2.price - l1.price)
        if gap >= 3 and diff <= tolerance:
            subtype = "micro" if gap <= 5 else "standard"
            return DetectorOutput(
                result_type="categorical", result="double_bottom",
                evidence={"l1_index": l1.bar_index, "l1_price": l1.price,
                          "l2_index": l2.bar_index, "l2_price": l2.price,
                          "diff": round(diff, 4), "tolerance": round(tolerance, 4),
                          "gap_bars": gap, "subtype": subtype},
            )

    # double_top：最近两个 swing_high 价差 ≤ tolerance，间隔 ≥3
    if len(highs) >= 2:
        h1, h2 = highs[-2], highs[-1]
        gap = h2.bar_index - h1.bar_index
        diff = abs(h2.price - h1.price)
        if gap >= 3 and diff <= tolerance:
            subtype = "micro" if gap <= 5 else "standard"
            return DetectorOutput(
                result_type="categorical", result="double_top",
                evidence={"h1_index": h1.bar_index, "h1_price": h1.price,
                          "h2_index": h2.bar_index, "h2_price": h2.price,
                          "diff": round(diff, 4), "tolerance": round(tolerance, 4),
                          "gap_bars": gap, "subtype": subtype},
            )
    return None


def register_complex() -> None:
    register(_meta_wedge, _fn_wedge)
    register(_meta_climax, _fn_climax)
    register(_meta_micro_channel, _fn_micro_channel)
    register(_meta_breakout, _fn_breakout)
    register(_meta_double, _fn_double)
