"""MVP-B detector 单测：正例/反例/边界/knowable_at（对应各 Concept Spec 的测试要求）。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.detectors.bar_facts import anatomy, register_bar_facts
from app.detectors.base import all_detectors
from app.detectors.patterns import register_patterns
from app.domain.bar import Bar, SessionType, Timeframe
from app.services.detector_service import compute_candidates

_T0 = datetime(2024, 6, 3, 13, 30, tzinfo=UTC)  # 09:30 ET


def mk(o: float, h: float, lo: float, c: float, i: int = 0) -> Bar:
    return Bar(
        instrument_id="SPY", timeframe=Timeframe.M5,
        ts_open_utc=_T0 + timedelta(minutes=5 * i),
        ts_close_utc=_T0 + timedelta(minutes=5 * (i + 1)),
        open=o, high=h, low=lo, close=c, volume=1000.0,
        session=SessionType.RTH, provider="synthetic", feed="t", data_version="t",
    )


def _setup():
    register_bar_facts()
    register_patterns()
    return all_detectors()


def test_anatomy_facts():
    bars = [mk(100, 110, 98, 108, 0)]  # bull，body=8，range=12
    f = anatomy(bars, 0)
    assert f["direction"] == "bull"
    assert f["body"] == 8 and f["range"] == 12
    assert f["body_ratio"] == round(8 / 12, 4)
    assert f["upper_tail_ratio"] == round(2 / 12, 4)
    assert f["lower_tail_ratio"] == round(2 / 12, 4)
    assert f["close_location"] == round(10 / 12, 4)
    assert f["relative_range"] is None  # 无历史
    assert not f["range_zero"]


def test_anatomy_zero_range_bar():
    bars = [mk(100, 100, 100, 100, 0)]
    f = anatomy(bars, 0)
    assert f["range_zero"] is True
    assert f["body_ratio"] is None and f["close_location"] is None


def test_relative_range_window():
    bars = [mk(100, 101, 99, 100, i) for i in range(21)]  # 每根 range=2
    bars[20] = mk(100, 105, 99, 104, 20)  # range=6
    f = anatomy(bars, 20)
    assert f["relative_range"] == 3.0  # 6 / 2


def _run(bars, i):
    dets = _setup()
    out = {}
    for k, det in dets.items():
        r = det.fn(bars, i)
        if r is not None:
            out[k] = r
    return out


def test_doji_positive_negative_boundary():
    # 正例：body_ratio 0.1
    r = _run([mk(100, 110, 100, 101, 0)], 0)
    assert r["doji"].result is True
    # 反例：body_ratio 0.6
    r2 = _run([mk(100, 110, 100, 106, 0)], 0)
    assert r2["doji"].result is False
    # 边界：恰 0.25（body 2.5 / range 10）→ 计入 doji（闭区间）
    r3 = _run([mk(100, 110, 100, 102.5, 0)], 0)
    assert r3["doji"].result is True
    # 零波幅 → doji
    r4 = _run([mk(100, 100, 100, 100, 0)], 0)
    assert r4["doji"].result is True


def test_trend_bar_strong_and_weak():
    # 强：body_ratio 0.8 且 relative_range ≥1.2（需 20 根历史）
    hist = [mk(100, 101, 99, 100, i) for i in range(20)]
    big = mk(100, 105.4, 100, 105, 20)  # range 5.4 = 2.7×均值, body 5 → ratio 0.926
    r = _run(hist + [big], 20)
    assert r["trend_bar"].result == "bull_trend_bar"
    assert r["trend_bar"].evidence["strong"] is True
    # 弱：body_ratio 0.4
    weak = mk(100, 102.5, 100, 101, 20)
    r2 = _run(hist + [weak], 20)
    assert r2["trend_bar"].result == "bull_trend_bar"
    assert r2["trend_bar"].evidence["strong"] is False
    # doji → none
    doji = mk(100, 102, 100, 100.2, 20)
    r3 = _run(hist + [doji], 20)
    assert r3["trend_bar"].result == "none"


def test_inside_outside_inclusive_ties():
    prev = mk(100, 110, 100, 105, 0)
    # 严格内包
    r = _run([prev, mk(104, 109, 101, 106, 1)], 1)
    assert r["inside_bar"].result is True and r["outside_bar"].result is False
    # 严格外包
    r2 = _run([prev, mk(104, 111, 99, 106, 1)], 1)
    assert r2["outside_bar"].result is True and r2["inside_bar"].result is False
    # 等号（inclusive）：高相等+低抬高的内包
    r3 = _run([prev, mk(104, 110, 101, 106, 1)], 1)
    assert r3["inside_bar"].result is True
    # 完全等幅：同时 inside 与 outside（spec 声明的并存边界）
    r4 = _run([prev, mk(104, 110, 100, 106, 1)], 1)
    assert r4["inside_bar"].result is True and r4["outside_bar"].result is True
    # 首根无前验：不判定（不输出候选）
    r5 = _run([prev], 0)
    assert "inside_bar" not in r5 and "outside_bar" not in r5


def test_pattern_ii_iii_ioi():
    # 收缩三连：ii 在第2根出现，iii 在第3根
    bars = [
        mk(100, 120, 98, 118, 0),
        mk(115, 119, 100, 110, 1),   # inside
        mk(110, 118, 101, 112, 2),   # inside → ii 在此
        mk(111, 117, 102, 113, 3),   # inside → iii 在此
    ]
    r1 = _run(bars, 2)
    assert r1["bar_pattern"].result == "ii"
    r2 = _run(bars, 3)
    assert r2["bar_pattern"].result == "iii"
    # ioi：inside, outside, inside
    bars2 = [
        mk(100, 110, 100, 105, 0),
        mk(104, 109, 101, 106, 1),   # inside
        mk(105, 111, 99, 107, 2),    # outside
        mk(106, 110.5, 100, 108, 3), # inside → ioi 在此
    ]
    r3 = _run(bars2, 3)
    assert r3["bar_pattern"].result == "ioi"
    # 序列中断：第二根突破 → 无事件
    bars3 = [mk(100, 110, 100, 105, 0), mk(104, 109, 101, 106, 1), mk(106, 112, 102, 108, 2)]
    assert "bar_pattern" not in _run(bars3, 2)


def test_signal_bar_evidence_fields():
    bars = [mk(100, 110, 100, 105, 0), mk(104, 109, 101, 106, 1)]
    r = _run(bars, 1)
    ev = r["signal_bar_evidence"].result
    assert ev["direction"] == "bull"
    assert ev["is_inside"] is True
    assert ev["is_outside"] is False
    assert ev["dominant_tail"] in ("upper", "lower", "none")
    assert 0 <= ev["close_location"] <= 1


def test_no_lookahead_by_construction():
    """在 ctx 后追加"未来"bar，i 处的判定结果不变。"""
    base = [
        mk(100, 120, 98, 118, 0),
        mk(115, 119, 100, 110, 1),
        mk(110, 118, 101, 112, 2),
    ]
    future = [mk(0, 999, 0, 500, 3), mk(999, 1000, 1, 2, 4)]
    without = _run(base, 2)
    with_future = _run(base + future, 2)
    for k in without:
        assert without[k].result == with_future[k].result
        assert without[k].evidence == with_future[k].evidence


def test_compute_candidates_bar_index_and_knowable():
    prefix = [mk(100, 101, 99, 100, i) for i in range(20)]
    visible = [mk(100, 110, 100, 105, 20), mk(104, 109, 101, 106, 21)]
    cands = compute_candidates(prefix, visible)
    assert all(c.bar_index in (0, 1) for c in cands)
    assert all(c.ts_knowable == visible[c.bar_index].ts_close_utc for c in cands)
    assert all(c.ts_knowable <= visible[-1].ts_close_utc for c in cands)
    ids = {c.detector_id for c in cands}
    assert {"bar_anatomy", "doji", "trend_bar", "signal_bar_evidence",
            "inside_bar", "outside_bar"} <= ids
    # 第 2 根是 inside → 事件型 bar_pattern 不触发（无 ii/ioi）
    assert "bar_pattern" not in ids
