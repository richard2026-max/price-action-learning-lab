"""detector 服务：对可见序列批量计算候选（Predict First 揭晓层）。

- ctx = 前日 RTH 5m（预热前视窗口数据，均为已收盘时段）+ 当日可见 RTH 5m；
- 候选只对"当日可见部分"输出，bar_index 为会话内下标；
- knowable_at = bar 收盘时刻（bar_close 精度），一律 ≤ cursor（no-lookahead）。
"""

from __future__ import annotations

from app.detectors.bar_facts import register_bar_facts
from app.detectors.base import Candidate, all_detectors
from app.detectors.complex import register_complex
from app.detectors.patterns import register_patterns
from app.detectors.structure import HL_STATE, register_structure
from app.domain.bar import Bar

_registered = False


def _ensure_registered() -> None:
    global _registered
    if not _registered:
        register_bar_facts()
        register_patterns()
        register_structure()
        register_complex()
        _registered = True


def compute_candidates(prefix: list[Bar], visible: list[Bar]) -> list[Candidate]:
    """prefix：前日RTH（仅供回看窗口）；visible：当日已可见（服务端裁剪后）。"""
    _ensure_registered()
    HL_STATE.reset()  # 状态机每会话计算从预热起点流式重放（幂等）
    ctx = prefix + visible
    offset = len(prefix)
    out: list[Candidate] = []
    detectors = all_detectors()
    for i in range(offset, len(ctx)):
        bar = ctx[i]
        for det_id, det in detectors.items():
            output = det.fn(ctx, i)
            if output is None:
                continue  # 事件型 detector：该 bar 无事件
            # swing 的事件归属确认根；极值根下标存于 evidence（会话内换算）
            if det_id == "swing" and isinstance(output.evidence.get("swing_bar_index"), int):
                output.evidence["swing_bar_index"] -= offset
            out.append(
                Candidate(
                    detector_id=det_id,
                    detector_version=det.meta.version,
                    bar_index=i - offset,
                    ts_event=bar.ts_close_utc,
                    ts_knowable=bar.ts_close_utc,
                    knowable_precision="bar_close",
                    result_type=det.meta.result_type,
                    result=output.result,
                    evidence=output.evidence,
                    rule_source="mechanical_definition",
                    provenance=det.meta.provenance,
                )
            )
    return out


def list_detector_metas() -> list[dict]:
    _ensure_registered()
    return [
        {
            "detector_id": m.meta.detector_id,
            "version": m.meta.version,
            "result_type": m.meta.result_type,
            "label": m.meta.label,
            "spec": m.meta.spec,
            "provenance": m.meta.provenance,
        }
        for m in all_detectors().values()
    ]
