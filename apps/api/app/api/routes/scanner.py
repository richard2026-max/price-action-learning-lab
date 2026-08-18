"""Scanner 路由（MVP-D 核心）。支持创建任务、查看进度、筛选候选列表与人工审核。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_scanner_service, resolve_instrument
from app.schemas.scanner import (
    CandidateRecordOut,
    CreateScanTaskIn,
    ReviewCandidateIn,
    ScanTaskOut,
)
from app.services.scanner_service import ScannerService

router = APIRouter(prefix="/scan", tags=["scanner"])


@router.post("/tasks", response_model=ScanTaskOut, status_code=201)
def create_task(
    req: CreateScanTaskIn,
    svc: ScannerService = Depends(get_scanner_service),
) -> ScanTaskOut:
    instrument = resolve_instrument(req.instrument_id, req.provider)
    try:
        orm = svc.create_and_run_task(req, instrument)
        return ScanTaskOut.model_validate(orm, from_attributes=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/tasks", response_model=list[ScanTaskOut])
def list_tasks(svc: ScannerService = Depends(get_scanner_service)) -> list[ScanTaskOut]:
    return [ScanTaskOut.model_validate(t, from_attributes=True) for t in svc.list_tasks()]


@router.get("/tasks/{task_id}", response_model=ScanTaskOut)
def get_task(task_id: str, svc: ScannerService = Depends(get_scanner_service)) -> ScanTaskOut:
    t = svc.get_task(task_id)
    if not t:
        raise HTTPException(status_code=404, detail="扫描任务不存在")
    return ScanTaskOut.model_validate(t, from_attributes=True)


@router.get("/candidates", response_model=list[CandidateRecordOut])
def list_candidates(
    task_id: str | None = Query(None),
    detector_id: str | None = Query(None),
    review_status: str | None = Query(None),
    only_favorites: bool = Query(False),
    only_mistakes: bool = Query(False),
    limit: int = Query(200, ge=1, le=1000),
    svc: ScannerService = Depends(get_scanner_service),
) -> list[CandidateRecordOut]:
    rows = svc.list_candidates(
        task_id=task_id,
        detector_id=detector_id,
        review_status=review_status,
        only_favorites=only_favorites,
        only_mistakes=only_mistakes,
        limit=limit,
    )
    return [CandidateRecordOut.model_validate(r, from_attributes=True) for r in rows]


@router.post("/candidates/{candidate_id}/review", response_model=CandidateRecordOut)
def review_candidate(
    candidate_id: str,
    req: ReviewCandidateIn,
    svc: ScannerService = Depends(get_scanner_service),
) -> CandidateRecordOut:
    updated = svc.review_candidate(candidate_id, req)
    if not updated:
        raise HTTPException(status_code=404, detail="候选记录不存在")
    return CandidateRecordOut.model_validate(updated, from_attributes=True)
