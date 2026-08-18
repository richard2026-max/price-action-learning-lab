"""MVP-C 结构层测试：swing 右侧确认、pullback 上下文、H/L 计数状态机、趋势线。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.detectors.bar_facts import register_bar_facts
from app.detectors.base import all_detectors
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
    HL_STATE.reset()
    return all_detectors()


def _run(bars, i):
    return all_detectors()["swing"].fn(bars, i)


def _run_hl(bars, i):
    return all_detectors()["hl_counting"].fn(bars, i)


def _run_pb(bars, i):
    return all_detectors()["pullback_leg"].fn(bars, i)


def _run_tl(bars, i):
    return all_detectors()["trend_lines"].fn(bars, i)


def test_swing_high_confirmed_after_right_side():
    _setup()
    bars = [
        mk(100, 104, 99, 103, 0), mk(101, 106, 100, 105, 1), mk(102, 108, 101, 107, 2),
        mk(103, 110, 102, 108, 3),   # 极值
        mk(104, 109, 103, 105, 4), mk(103, 108, 102, 104, 5), mk(102, 107, 101, 103, 6),
    ]
    out = _run(bars, 6)
    assert out is not None and out.result == "swing_high"
    assert out.evidence["swing_bar_index"] == 3
    assert _run(bars, 5) is None


def test_swing_low_symmetric():
    _setup()
    bars = [
        mk(110, 111, 108, 109, 0), mk(108, 110, 105, 109, 1), mk(107, 109, 102, 108, 2),
        mk(103, 106, 100, 105, 3),   # 极值低
        mk(104, 107, 101, 106, 4), mk(105, 108, 102, 107, 5), mk(106, 109, 103, 108, 6),
    ]
    out = _run(bars, 6)
    assert out is not None and out.result == "swing_low"
    assert out.evidence["swing_bar_index"] == 3


def test_pullback_context_direction():
    _setup()
    up = [mk(100 + i, 102 + i, 99 + i, 101 + i, i) for i in range(21)]
    up[20] = mk(119, 121, 118, 120, 20)
    pull = mk(118, 120, 117, 119, 21)
    bars = up + [pull]
    out = _run_pb(bars, 21)
    assert out is not None and out.result == "bull_pullback"

    down = [mk(200 - i, 202 - i, 199 - i, 201 - i, i) for i in range(21)]
    down[20] = mk(181, 183, 180, 182, 20)
    cont = mk(180, 182, 179, 181, 21)
    out2 = _run_pb(down + [cont], 21)
    assert out2 is not None and out2.result == "none"


def test_hl_counting_sequence():
    _setup()
    seq = []
    price = 100.0
    for i in range(20):
        seq.append(mk(price, price + 1, price - 1, price + 0.5, i))
        price += 1
    seq.append(mk(price, price + 0.3, price - 1.5, price - 0.5, 20))
    seq.append(mk(price - 0.5, price - 0.2, price - 2.0, price - 0.8, 21))
    seq.append(mk(price - 0.8, price + 1.2, price - 1.0, price + 0.8, 22))
    out1 = _run_hl(seq, 22)
    assert out1 is not None and out1.result == "H1"
    assert out1.evidence["second_entry"] is False

    seq.append(mk(price + 0.8, price + 1.0, price - 0.5, price + 0.6, 23))
    assert _run_hl(seq, 23) is None
    seq.append(mk(price + 0.6, price + 2.0, price + 0.4, price + 1.8, 24))
    out2 = _run_hl(seq, 24)
    assert out2 is not None and out2.result == "H2"
    assert out2.evidence["second_entry"] is True

    seq.append(mk(price + 1.8, price + 3.0, price + 1.5, price + 2.8, 25))
    assert _run_hl(seq, 25) is None


def test_trend_line_construction_and_breakout():
    _setup()
    # 构造含两个抬高 swing_low 的序列
    # Low 1 在 i=3 (L=95.0), 确认在 i=6 (k=4,5,6 L=96,97,98 > 95)
    # 之后价格上涨至 i=6 (L=98.0, H=103), i=7 (L=101.5), i=8 (L=101.0)
    # Low 2 在 i=9 (L=97.0 > 95.0, 且低于左侧 6/7/8: 98.0/101.5/101.0 -> 成立)
    # 右侧 i=10,11,12 (L=99.0, 100.0, 101.0 > 97.0) -> 在 i=12 确认 Low 2
    bars = [
        mk(100, 102, 98, 101, 0), mk(101, 102, 97, 98, 1), mk(98, 99, 96, 97, 2),
        mk(97, 98, 95.0, 96, 3),    # Low 1 (L=95.0)
        mk(96, 99, 96.0, 98, 4), mk(98, 101, 97.0, 100, 5), mk(100, 103, 98.0, 102, 6),  # 确认 Low 1
        mk(102, 104, 101.5, 103, 7), mk(103, 104, 101.0, 102, 8),
        mk(100, 101, 97.0, 99, 9),  # Low 2 (L=97.0 > 95.0, 且低于 98.0/101.5/101.0)
        mk(99, 102, 99.0, 101, 10), mk(101, 104, 100.0, 103, 11), mk(103, 106, 101.0, 105, 12), # 确认 Low 2
    ]
    # 在 i=12 时应检测到有效上升趋势线
    out = _run_tl(bars, 12)
    assert out is not None
    res = out.result
    assert res["bull_trend_line"] is not None
    bull = res["bull_trend_line"]
    assert bull["p1_index"] == 3 and bull["p1_price"] == 95.0
    assert bull["p2_index"] == 9 and bull["p2_price"] == 97.0
    assert bull["slope"] > 0
    assert not bull["breakout"]

    # 在 i=13 价格深跌跌破该线 -> 触发 breakout
    bars.append(mk(105, 105.5, 90.0, 91.0, 13))
    out_bo = _run_tl(bars, 13)
    assert out_bo is not None and out_bo.result["bull_trend_line"]["breakout"] is True
