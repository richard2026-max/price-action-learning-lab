"""Level 5 高级形态测试（spike_and_channel / final_flag）。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.detectors.advanced import register_advanced
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
    register_advanced()
    HL_STATE.reset()
    return all_detectors()


def test_spike_and_channel_bull():
    _setup()
    det = all_detectors()["spike_and_channel"]
    bars = []

    # Phase A: spike - 3 根大阳线，每根 body_ratio >= 0.6
    bars.append(mk(100, 103, 99.8, 102.5, 0))       # br=0.78
    bars.append(mk(102.5, 105.5, 102.2, 105.2, 1))  # br=0.82
    bars.append(mk(105.2, 107, 105.0, 106.8, 2))    # br=0.80

    # Phase B: channel - 6 根小K线缓慢推进 (body_ratio ~0.19)
    price = 106.8
    for j in range(3, 9):
        bars.append(mk(price, price + 0.4, price - 0.4, price + 0.15, j))
        price += 0.15

    out = det.fn(bars, len(bars) - 1)
    assert out is not None, "spike_and_channel 未检测到"
    assert out.result == "bull_spike_and_channel"
    assert out.evidence["spike_bars"] >= 2


def test_final_flag_after_climax():
    _setup()
    det = all_detectors()["final_flag"]

    # 构造：20 根常规 + 3 根大阳线 climax + 4 根窄幅旗形
    bars = [mk(100, 100.3, 99.8, 100.1, i) for i in range(20)]  # 常规均幅 ~1.0

    p = 100.2
    for j in range(20, 23):
        bars.append(mk(p, p + 2.5, p - 0.5, p + 2.0, j))
        p += 1.8

    flag_start = p
    for j in range(23, 27):
        if j % 2 == 0:
            bars.append(mk(flag_start - 0.2, flag_start + 0.3, flag_start - 0.5, flag_start + 0.1, j))
        else:
            bars.append(mk(flag_start + 0.1, flag_start + 0.4, flag_start - 0.3, flag_start - 0.1, j))

    out = det.fn(bars, len(bars) - 1)
    assert out is not None, "final_flag 未检测到"
    assert "final_flag" in out.result
