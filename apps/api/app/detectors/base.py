"""detector 基础设施：Candidate 结构、Detector 协议、注册表。

原则（PRD §五、concepts/README.md）：
- detector 是薄模块，只做机械判定，全部可解释 evidence；
- result_type 多样（boolean/categorical/evidence_set），不强制 0-1 score；
- detect(ctx, i) 只允许访问 ctx[0..i]——no lookahead by construction；
- 每个 detector 注册时声明 concept spec 路径与 provenance 分层。
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime

from app.domain.bar import Bar
from app.structure.profile import DETECTOR_PROFILE_VERSION, params, profile_version  # noqa: F401


@dataclass(frozen=True, slots=True)
class Candidate:
    detector_id: str
    detector_version: str
    bar_index: int  # 会话内 RTH 序列下标（从 0 起）
    ts_event: datetime
    ts_knowable: datetime
    knowable_precision: str
    result_type: str
    result: object
    evidence: dict = field(default_factory=dict)
    rule_source: str = "mechanical_definition"
    provenance: str = "Mechanical Approximation"


@dataclass(frozen=True, slots=True)
class DetectorMeta:
    detector_id: str
    version: str
    result_type: str
    label: str  # 中文标签
    spec: str  # docs/concepts/<x>.md
    provenance: str


# 每根 bar 的输出；None 表示该 bar 无事件（event 型 detector）
DetectFn = Callable[[Sequence[Bar], int], "DetectorOutput | None"]


@dataclass(frozen=True, slots=True)
class DetectorOutput:
    result_type: str
    result: object
    evidence: dict


@dataclass(frozen=True, slots=True)
class Detector:
    meta: DetectorMeta
    fn: DetectFn


_REGISTRY: dict[str, Detector] = {}


def register(meta: DetectorMeta, fn: DetectFn) -> None:
    _REGISTRY[meta.detector_id] = Detector(meta=meta, fn=fn)


def all_detectors() -> dict[str, Detector]:
    return dict(_REGISTRY)
