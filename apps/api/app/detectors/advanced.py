"""Level 5 高级形态识别器：spike_and_channel / final_flag。

对应 specs：docs/concepts/spike-and-channel.md, final-flag.md。
基于已确认 Swing、K线解剖事实与 climax 事件组合，严格无前视。
"""

from __future__ import annotations

from collections.abc import Sequence

from app.detectors.bar_facts import anatomy
from app.detectors.base import DetectorMeta, DetectorOutput, register
from app.domain.bar import Bar
from app.structure.profile import params

# ---------------- spike_and_channel (尖刺+通道) ----------------
_meta_spike_channel = DetectorMeta(
    detector_id="spike_and_channel",
    version="0.1.0",
    result_type="categorical",
    label="尖刺+通道",
    spec="docs/concepts/spike-and-channel.md",
    provenance="Mechanical Approximation",
)

_SPIKE_MIN_BARS = 2
_CHANNEL_MIN_BARS = 4


def _fn_spike_and_channel(ctx: Sequence[Bar], i: int) -> DetectorOutput | None:
    """简化两阶段判定：前半段强趋势棒(spike) + 后半段弱K线(channel)。"""
    min_total = _SPIKE_MIN_BARS + _CHANNEL_MIN_BARS
    if i < min_total:
        return None

    # 在 ctx 中向前搜索 spike→channel 分界点
    for split in range(_SPIKE_MIN_BARS, i - _CHANNEL_MIN_BARS + 1):
        spike_bars = list(ctx[split - _SPIKE_MIN_BARS : split + 1])
        chan_bars = list(ctx[split + 1 : i + 1])
        if len(chan_bars) < _CHANNEL_MIN_BARS:
            continue

        # Phase A: spike 检测——所有 bar 同向 strong trend_bar，总位移大
        directions = set()
        total_move = abs(spike_bars[-1].close - spike_bars[0].open)
        all_strong = True
        spike_body_sum = 0.0

        for sb in spike_bars:
            sf = anatomy([sb], 0)
            directions.add(sf["direction"])
            br = sf["body_ratio"]
            if br is None or br < float(params()["trend_bar_strong_body_ratio"]):
                all_strong = False
            spike_body_sum += br if br is not None else 0.5

        avg_spike_br = spike_body_sum / len(spike_bars)

        if not all_strong or len(directions) != 1:
            continue

        direction = "bull" if "bull" in directions else "bear"
        lookback = min(i, int(params()["relative_range_window"]))
        if lookback <= 0:
            continue
        avg_rng = sum(ctx[k].high - ctx[k].low for k in range(max(0, i - lookback), i)) / max(1, lookback)
        if avg_rng <= 0 or total_move < avg_rng * 2.0:
            continue

        # Phase B: channel 检测——body_ratio 均值 < spike 的 60%
        chan_body_sum = 0.0
        for cb in chan_bars:
            cf = anatomy([cb], 0)
            chan_body_sum += cf["body_ratio"] if cf["body_ratio"] is not None else 0.3
        chan_avg_br = chan_body_sum / len(chan_bars)

        if chan_avg_br < avg_spike_br * 0.6:
            res = f"{direction}_spike_and_channel"
            return DetectorOutput(
                result_type="categorical",
                result=res,
                evidence={
                    "spike_bars": len(spike_bars),
                    "channel_bars": len(chan_bars),
                    "total_move": round(total_move, 4),
                    "spike_body_ratio": round(avg_spike_br, 4),
                    "channel_body_ratio": round(chan_avg_br, 4),
                    "momentum_decay": round(1 - chan_avg_br / max(avg_spike_br, 0.01), 4),
                },
            )

    return None


# ---------------- final_flag (终极旗形) ----------------
_meta_final_flag = DetectorMeta(
    detector_id="final_flag",
    version="0.1.0",
    result_type="categorical",
    label="终极旗形",
    spec="docs/concepts/final-flag.md",
    provenance="Mechanical Approximation",
)


def _fn_final_flag(ctx: Sequence[Bar], i: int) -> DetectorOutput | None:
    """climax 后 + 窄幅旗形停顿 = final flag candidate。"""
    if i < 8:
        return None

    # 向前搜索 climax（最近 10 根内），直接用 anatomy 内联检测而非调用其他 detector
    climax_dir = None
    climax_bar_idx = None

    for back in range(2, 11):
        check_i = i - back
        if check_i < 0:
            break
        cf = anatomy(ctx, check_i)  # 使用完整 ctx 以便计算 relative_range
        rr = cf["relative_range"]
        br = cf["body_ratio"]
        climax_rr_threshold = float(params().get("climax_exhaustion_relative_range", 2.6))
        if rr is not None and rr >= climax_rr_threshold and br is not None and br >= 0.55:
            climax_dir = "long" if cf["direction"] == "bull" else "short"
            climax_bar_idx = check_i
            break

    if climax_dir is None or climax_bar_idx is None:
        return None

    # climax 之后到当前的窄幅旗形阶段
    flag_bars = ctx[climax_bar_idx + 1 : i + 1]
    if not (3 <= len(flag_bars) <= 10):
        return None

    body_sum = 0.0
    for fb in flag_bars:
        ff = anatomy(flag_bars, flag_bars.index(fb))
        br = ff["body_ratio"]
        body_sum += br if br is not None else 0

    avg_body = body_sum / len(flag_bars)
    if avg_body >= 0.5:
        return None

    # climax 位移计算
    pre_idx = max(0, climax_bar_idx - 2)
    climax_span = abs(ctx[climax_bar_idx].close - ctx[pre_idx].open)
    if climax_span <= 0:
        return None

    if climax_dir == "long":
        climax_bar_high = ctx[climax_bar_idx].high
        extreme = max(b.high for b in ctx[climax_bar_idx : i + 1])
        extension = extreme - climax_bar_high
    else:
        climax_bar_low = ctx[climax_bar_idx].low
        extreme = min(b.low for b in ctx[climax_bar_idx : i + 1])
        extension = climax_bar_low - extreme

    if extension > climax_span * 0.5:
        return None

    res = f"{'bull' if climax_dir == 'long' else 'bear'}_final_flag"
    return DetectorOutput(
        result_type="categorical",
        result=res,
        evidence={
            "climax_bar_index": climax_bar_idx,
            "flag_bars": len(flag_bars),
            "avg_body_ratio": round(avg_body, 4),
            "climax_span": round(climax_span, 4),
            "extension": round(extension, 4),
            "extension_ratio": round(extension / climax_span, 4),
        },
    )


def register_advanced() -> None:
    register(_meta_spike_channel, _fn_spike_and_channel)
    register(_meta_final_flag, _fn_final_flag)
