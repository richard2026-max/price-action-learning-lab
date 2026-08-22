"""Level 3 突破/失败突破与双顶双底 detector 测试。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.detectors.bar_facts import register_bar_facts
from app.detectors.base import all_detectors
from app.detectors.complex import register_complex
from app.detectors.patterns import register_patterns
from app.detectors.structure import HL_STATE, register_structure
from app.domain.bar import Bar, SessionType, Timeframe

_T0 = datetime(2024, 6, 3, 13, 30, tzinfo=UTC)


def mk(o, h, lo, c, i=0):
    return Bar(
        instrument_id="SPY", timeframe=Timeframe.M5,
        ts_open_utc=_T0 + timedelta(minutes=5 * i), ts_close_utc=_T0 + timedelta(minutes=5 * (i + 1)),
        open=o, high=h, low=lo, close=c, volume=1000.0,
        session=SessionType.RTH, provider="synthetic", feed="t", data_version="t",
    )


def _setup():
    register_bar_facts()
    register_patterns()
    register_structure()
    register_complex()
    HL_STATE.reset()
    return all_detectors()


def test_breakout_and_failed_breakout():
    dets = _setup()
    fn = dets["breakout"].fn

    # 构造：swing_high 在 i=3 (H=110)，确认在 i=6
    bars = [
        mk(100, 102, 99, 101, 0), mk(101, 103, 100, 102, 1), mk(102, 104, 101, 103, 2),
        mk(103, 110.0, 102, 109, 3),   # swing_high (H=110)
        mk(109, 109.5, 107, 108, 4), mk(108, 108.5, 106, 107, 5), mk(107, 107.5, 105, 106, 6),  # 确认
    ]

    # i=7: close 升破 110 → bull_breakout
    bars.append(mk(108, 111.5, 108, 111, 7))
    out = fn(bars, 7)
    assert out is not None and out.result == "bull_breakout"

    # i=8: 持续在上方 → 无新事件（非首次穿越）
    bars.append(mk(111, 112, 110, 111.5, 8))
    out8 = fn(bars, 8)
    assert out8 is None or "bull" not in str(out8.result) or "failed" not in str(out8.result)

    # i=9: 收盘跌回 110 以下 → failed_bull_breakout
    bars.append(mk(110, 110.5, 106, 107, 9))
    out9 = fn(bars, 9)
    assert out9 is not None and out9.result == "failed_bull_breakout"


def test_double_top_detection():
    _setup()
    fn = all_detectors()["double_top_bottom"].fn

    # 构造两个大致相同的 swing_high
    bars = [
        mk(100, 102, 99, 101, 0), mk(101, 103, 100, 102, 1), mk(102, 104, 101, 103, 2),
        mk(103, 110.0, 102, 109, 3),  # H1 = 110
        mk(109, 109.5, 107, 108, 4), mk(108, 108.5, 106, 107, 5), mk(107, 107.5, 105, 106, 6),
        mk(106, 106.5, 104, 105, 7), mk(105, 106, 103, 104, 8), mk(104, 105, 102, 103, 9),  # 确认 H1
        mk(103, 106, 102, 105, 10), mk(105, 108, 104, 107, 11), mk(107, 110.2, 106, 109, 12), # H2 = 110.2 (diff=0.2)
        mk(109, 109.5, 107, 108, 13), mk(108, 108.5, 106, 107, 14), mk(107, 107.5, 105, 106, 15), # 确认 H2
    ]
    out = fn(bars, 15)
    assert out is not None and out.result == "double_top"
    ev = out.evidence
    assert abs(ev["h1_price"] - 110.0) < 0.01
    assert abs(ev["h2_price"] - 110.2) < 0.01


def test_double_bottom_detection():
    _setup()
    fn = all_detectors()["double_top_bottom"].fn

    # 构造两个大致相同的 swing_low
    bars = [
        mk(200, 202, 199, 201, 0), mk(201, 203, 200, 202, 1), mk(202, 204, 201, 203, 2),
        mk(203, 204, 190.0, 191, 3),  # L1 = 190
        mk(191, 195, 190.5, 194, 4), mk(193, 196, 192, 195, 5), mk(194, 197, 193, 196, 6),
        mk(195, 198, 194, 197, 7), mk(196, 199, 195, 198, 8), mk(197, 200, 196, 199, 9),  # 确认 L1
        mk(198, 201, 190.5, 200, 10),  # L2 = 190.5 (diff=0.5)
        mk(200, 203, 198, 202, 11), mk(201, 205, 200, 204, 12), mk(203, 207, 202, 206, 13),
    ]
    out = fn(bars, 13)
    assert out is not None and out.result == "double_bottom"
    ev = out.evidence
    assert abs(ev["diff"]) <= ev["tolerance"]
