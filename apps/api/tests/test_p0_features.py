"""Always In 状态机与知识库检索测试（P0）。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.detectors.always_in import AI_STATE, register_always_in
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
    register_always_in()
    HL_STATE.reset()
    AI_STATE.reset()
    return all_detectors()


def _build_swing_uptrend():
    seq = []
    seq += [mk(100 + i, 103 + i, 99 + i, 102 + i, i) for i in range(3)]
    seq.append(mk(104, 110, 103, 109, 3))   # peak
    seq.append(mk(108, 108.5, 105, 106, 4))
    seq.append(mk(106, 106.5, 104, 104.5, 5))
    seq.append(mk(105, 105.5, 103.5, 104, 6))
    seq.append(mk(105, 107, 104, 106, 7))
    seq.append(mk(106, 109, 105, 108, 8))
    seq.append(mk(108, 112, 107, 111, 9))   # new high (HH)
    seq.append(mk(110, 110.5, 107, 108, 10))
    seq.append(mk(108, 108.5, 106, 107, 11))
    seq.append(mk(107, 107.5, 105.5, 106.5, 12))
    seq.append(mk(107, 109, 106, 108, 13))
    seq.append(mk(108, 111, 107, 110, 14))
    seq.append(mk(110, 114, 109, 113, 15))  # higher high
    return seq


def _build_swing_downtrend():
    seq = []
    seq += [mk(200 - i, 203 - i, 199 - i, 198 - i, i) for i in range(3)]
    seq.append(mk(196, 197, 190, 191, 3))
    seq.append(mk(192, 195, 191, 194, 4))
    seq.append(mk(194, 196, 192, 195, 5))
    seq.append(mk(195, 196, 188, 189, 6))   # lower low
    seq.append(mk(189, 193, 188.5, 192, 7))
    seq.append(mk(192, 194, 191, 193, 8))
    seq.append(mk(193, 193.5, 185, 186, 9))  # lower low
    return seq


def test_always_in_via_compute_candidates():
    """通过 compute_candidates 全流程验证（确保 HL 状态机正确推进）。"""
    from app.services.detector_service import compute_candidates

    _setup()
    prefix = [mk(100, 101, 99, 100, i) for i in range(20)]
    seq = _build_swing_uptrend()
    candidates = compute_candidates(prefix, seq)

    ai_events = [c for c in candidates if c.detector_id == "always_in"]
    long_events = [c for c in ai_events if "long" in str(c.result)]
    assert len(long_events) > 0, f"未检测到 always_in_long，ai_events={[(c.bar_index, c.result) for c in ai_events]}"


def test_knowledge_search():
    from app.services.knowledge_service import KnowledgeService

    svc = KnowledgeService()
    results = svc.search("inside bar", max_results=10)
    assert len(results) > 0
    first = results[0]
    assert first.book_code in ("T", "R", "REV")
    assert first.pdf_page > 0

    # always in 应命中多本书的多个页面
    ai_results = svc.search("always in", max_results=20)
    assert len(ai_results) >= 3


def test_knowledge_search_by_concept():
    from app.services.knowledge_service import KnowledgeService

    svc = KnowledgeService()
    results = svc.search_by_concept("wedge")
    assert len(results) > 0


def test_detector_registry_has_15():
    _setup()
    assert len(all_detectors()) == 19  # 11 prior + wedge/climax/micro_channel/always_in/signal_bar_evidence
