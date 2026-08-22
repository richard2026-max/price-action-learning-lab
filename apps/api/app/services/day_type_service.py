"""日类型统计服务（Day Type Classification, Level 4 市场环境）。

基于当日 RTH 5m K线序列的客观几何特征，将交易日分类为 Brooks 描述的常见日类型：
- trend_from_open_bull: 开盘后持续上行，收盘接近高点
- trend_from_open_bear: 开盘后持续下行，收盘接近低点
- trading_range_day: 窄幅区间震荡，开盘与收盘接近
- spike_and_channel_day: 急速突破 + 缓慢通道
- other: 不符合上述模式

所有判定基于收盘后的完整数据（post-hoc analysis），不用于实时回放。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.bar import Bar


@dataclass(frozen=True, slots=True)
class DayTypeResult:
    day_type: str
    confidence: str  # good / okay / bad
    evidence: dict


def _range_of(bars: Sequence[Bar]) -> float:
    return max(b.high for b in bars) - min(b.low for b in bars)


def classify_day(rth_bars: list[Bar]) -> DayTypeResult:
    """对已完成交易日进行日类型分类（仅用于复盘分析，非实时）。"""
    if len(rth_bars) < 10:
        return DayTypeResult(day_type="insufficient_data", confidence="bad", evidence={})

    n = len(rth_bars)
    open_price = rth_bars[0].open
    close_price = rth_bars[-1].close
    high = max(b.high for b in rth_bars)
    low = min(b.low for b in rth_bars)
    day_range = high - low

    if day_range <= 0:
        return DayTypeResult(day_type="flat", confidence="bad", evidence={"day_range": 0})

    # 关键位置比例
    close_position = (close_price - low) / day_range  # 0=最低 1=最高

    # 前1/3 vs 后2/3 方向一致性
    first_third = rth_bars[: max(1, n // 3)]
    first_dir = first_third[-1].close - first_third[0].open

    # 净位移占比
    net_move = abs(close_price - open_price)
    net_ratio = net_move / day_range if day_range > 0 else 0

    # 中间K线的重叠度（区间日特征）
    overlaps = sum(
        1 for i in range(1, n) if rth_bars[i].low <= rth_bars[i - 1].high and rth_bars[i].high >= rth_bars[i - 1].low
    )
    overlap_ratio = overlaps / (n - 1)

    # 最大连续同向趋势棒数
    max_streak = 0
    streak = 0
    prev_dir = ""
    for b in rth_bars:
        d = "bull" if b.close > b.open else ("bear" if b.close < b.open else "")
        if d and d == prev_dir:
            streak += 1
        elif d:
            streak = 1
        else:
            streak = 0
        max_streak = max(max_streak, streak)
        prev_dir = d

    evidence = {
        "open": round(open_price, 2),
        "close": round(close_price, 2),
        "high": round(high, 2),
        "low": round(low, 2),
        "day_range": round(day_range, 2),
        "net_move_ratio": round(net_ratio, 4),
        "close_position": round(close_position, 4),
        "overlap_ratio": round(overlap_ratio, 4),
        "max_consecutive_trend_bars": max_streak,
        "first_third_direction": "up" if first_dir > 0 else ("down" if first_dir < 0 else "flat"),
    }

    # 分类规则（按优先级）
    if net_ratio >= 0.55 and close_position >= 0.75 and first_dir > 0:
        conf = "good" if net_ratio >= 0.7 else "okay"
        return DayTypeResult("trend_from_open_bull", conf, evidence)

    if net_ratio >= 0.55 and close_position <= 0.25 and first_dir < 0:
        conf = "good" if net_ratio >= 0.7 else "okay"
        return DayTypeResult("trend_from_open_bear", conf, evidence)

    if net_ratio <= 0.20 and overlap_ratio >= 0.70:
        conf = "good" if net_ratio <= 0.10 else "okay"
        return DayTypeResult("trading_range_day", conf, evidence)

    # 尖刺+通道：前1/3大幅单向，后续缓慢推进
    spike_move = abs(first_third[-1].close - first_third[0].open)
    if spike_move >= day_range * 0.5:
        direction = "bull" if first_dir > 0 else "bear"
        return DayTypeResult(f"spike_and_channel_{direction}_day", "okay", evidence)

    return DayTypeResult("other", "bad", evidence)


def classify_days_batch(all_days_data: dict[str, list[Bar]]) -> dict[str, dict]:
    """批量分类多天数据。"""
    results = {}
    for day_iso, bars in sorted(all_days_data.items()):
        r = classify_day(bars)
        results[day_iso] = {
            "day_type": r.day_type,
            "confidence": r.confidence,
            **r.evidence,
        }
    return results
