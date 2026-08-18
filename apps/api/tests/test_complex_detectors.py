"""Level 5 复杂形态 Detectors 测试（Wedge, Climax, Micro Channel）。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.detectors.bar_facts import register_bar_facts
from app.detectors.base import all_detectors
from app.detectors.complex import register_complex
from app.detectors.patterns import register_patterns
from app.detectors.structure import HL_STATE, register_structure
from app.domain.bar import Bar, SessionType, Timeframe

_T0 = datetime(2024, 6, 3, 13, 30, tzinfo=UTC)


def mk(o, h, lo, c, i=0, v=1000.0):
    return Bar(
        instrument_id="SPY", timeframe=Timeframe.M5,
        ts_open_utc=_T0 + timedelta(minutes=5 * i), ts_close_utc=_T0 + timedelta(minutes=5 * (i + 1)),
        open=o, high=h, low=lo, close=c, volume=v,
        session=SessionType.RTH, provider="synthetic", feed="t", data_version="t",
    )


def _setup():
    register_bar_facts()
    register_patterns()
    register_structure()
    register_complex()
    HL_STATE.reset()
    return all_detectors()


def test_micro_channel_bull_and_bear():
    _setup()
    # 构造连续 5 根不破前低的强多头微通道 (low[k] >= low[k-1])
    bars = [
        mk(100, 102, 99.0, 101.5, 0),
        mk(101.5, 103, 100.0, 102.5, 1),
        mk(102.5, 104, 101.0, 103.5, 2),
        mk(103.5, 105, 102.0, 104.5, 3),  # 第 4 根，达到 min_len=4
        mk(104.5, 106, 103.0, 105.5, 4),  # 第 5 根，长度 5
    ]
    det = all_detectors()["micro_channel"]

    # 前 3 根不足 4 根 -> None
    assert det.fn(bars, 2) is None

    # 第 4 根 (i=3) -> bull_micro_channel (len=4)
    out_4 = det.fn(bars, 3)
    assert out_4 is not None and out_4.result == "bull_micro_channel"
    assert out_4.evidence["channel_length"] == 4

    # 第 5 根 (i=4) -> 长度累加至 5
    out_5 = det.fn(bars, 4)
    assert out_5 is not None and out_5.result == "bull_micro_channel"
    assert out_5.evidence["channel_length"] == 5

    # 第 6 根跌破前低 (L=102.0 < L=103.0) -> 微通道中断
    bars.append(mk(105, 105.5, 102.0, 102.5, 5))
    assert det.fn(bars, 5) is None


def test_climax_single_exhaustion_bar():
    _setup()
    # 构造 20 根常规均幅波段 (range ~ 1.0)
    bars = [mk(100, 100.5, 99.5, 100.2, i) for i in range(20)]
    # i=20 出现 3.5 倍波幅的大阳线 (range=3.5, body=3.2)
    climax_bar = mk(100, 103.5, 100, 103.2, 20)
    bars.append(climax_bar)

    det = all_detectors()["climax"]
    out = det.fn(bars, 20)
    assert out is not None
    assert out.result == "buy_climax"
    assert out.evidence["type"] == "single_exhaustion_bar"


def test_wedge_three_pushes():
    _setup()
    # 构造三推上升楔形：
    # Push 1 在 i=3 (H=105), 确认在 i=6
    # Push 2 在 i=9 (H=109), 确认在 i=12 (增幅 push1 = 4.0)
    # Push 3 在 i=15 (H=112), 确认在 i=18 (增幅 push2 = 3.0 < 4.0 涨幅衰减)
    bars = [
        # Push 1
        mk(100, 102, 99, 101, 0), mk(101, 103, 100, 102, 1), mk(102, 104, 101, 103, 2),
        mk(103, 105.0, 102, 104, 3), # H1 = 105.0
        mk(104, 104.5, 102, 103, 4), mk(103, 104.0, 101, 102, 5), mk(102, 103.5, 100, 101, 6), # 确认 H1
        # Push 2
        mk(101, 106, 101, 105, 7), mk(105, 108, 104, 107, 8),
        mk(107, 109.0, 106, 108, 9), # H2 = 109.0
        mk(108, 108.5, 106, 107, 10), mk(107, 108.0, 105, 106, 11), mk(106, 107.5, 104, 105, 12), # 确认 H2
        # Push 3
        mk(105, 110, 105, 109, 13), mk(109, 111, 108, 110, 14),
        mk(110, 112.0, 109, 111, 15), # H3 = 112.0
        mk(111, 111.5, 109, 110, 16), mk(110, 111.0, 108, 109, 17), mk(109, 110.5, 107, 108, 18), # 确认 H3
    ]

    det = all_detectors()["wedge"]
    out = det.fn(bars, 18)
    assert out is not None
    assert out.result == "rising_wedge"
    assert out.evidence["pushes"] == [105.0, 109.0, 112.0]
    assert out.evidence["push1_gain"] == 4.0
    assert out.evidence["push2_gain"] == 3.0
