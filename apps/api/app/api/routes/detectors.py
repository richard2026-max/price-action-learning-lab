"""detector 元数据路由。"""

from __future__ import annotations

from fastapi import APIRouter

from app.services.detector_service import list_detector_metas
from app.structure.profile import DETECTOR_PROFILE_VERSION, PARAMS

router = APIRouter(prefix="/detectors", tags=["detectors"])


@router.get("")
def detectors() -> dict:
    """已注册 detector 清单（含 Concept Spec 路径与 provenance 分层）。"""
    return {
        "profile_version": DETECTOR_PROFILE_VERSION,
        "params": PARAMS,
        "detectors": list_detector_metas(),
    }
