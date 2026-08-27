"""回放路由（MVP-A 核心）。所有行情响应经 ReplayService 服务端裁剪（no-lookahead）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.deps import get_replay_service, resolve_instrument
from app.replay.service import ReplayError, ReplayService
from app.schemas.replay import (
    AdvanceIn,
    AnnotationIn,
    AnnotationOut,
    CreateSessionIn,
    JudgmentIn,
    JudgmentOut,
    SessionDetailOut,
)

router = APIRouter(prefix="/replay", tags=["replay"])


def _http(e: ReplayError) -> HTTPException:
    return HTTPException(status_code=e.status, detail={"code": e.code, "message": e.message})


@router.get("/days")
def available_days(
    instrument_id: str = "SPY",
    provider: str = "synthetic",
    include_sealed: bool = Query(False, description="是否包含封存考试日（普通训练默认排除）"),
    svc: ReplayService = Depends(get_replay_service),
) -> dict:
    instrument = resolve_instrument(instrument_id, provider)
    return {"days": svc.available_days(instrument, include_sealed=include_sealed)}


@router.get("/exam-summary")
def exam_summary(
    instrument_id: str = "SPY",
    provider: str = "synthetic",
    svc: ReplayService = Depends(get_replay_service),
) -> dict:
    """获取数据集封存集统计信息（用于质量报告与考试准备）。"""
    from app.services.sealed_exam import get_exam_split_summary

    instrument = resolve_instrument(instrument_id, provider)
    all_days = svc.available_days(instrument, include_sealed=True)
    return get_exam_split_summary(all_days)


@router.get("/random-day")
def random_day(
    seed: int = Query(..., description="随机种子（可复现）"),
    instrument_id: str = "SPY",
    provider: str = "synthetic",
    for_exam: bool = Query(False, description="是否从封存考试集中抽取"),
    svc: ReplayService = Depends(get_replay_service),
) -> dict:
    instrument = resolve_instrument(instrument_id, provider)
    try:
        return {"day": svc.random_day(instrument, seed, for_exam=for_exam)}
    except ReplayError as e:
        raise _http(e) from None


@router.post("/sessions", response_model=SessionDetailOut)
def create_session(
    req: CreateSessionIn,
    svc: ReplayService = Depends(get_replay_service),
) -> SessionDetailOut:
    instrument = resolve_instrument(req.instrument_id, req.provider)
    try:
        return svc.create(req, instrument)
    except ReplayError as e:
        raise _http(e) from None


@router.get("/sessions/{session_id}", response_model=SessionDetailOut)
def get_session(
    session_id: str,
    provider: str = "synthetic",
    instrument_id: str = "SPY",
    svc: ReplayService = Depends(get_replay_service),
) -> SessionDetailOut:
    instrument = resolve_instrument(instrument_id, provider)
    try:
        return svc.get(session_id, instrument)
    except ReplayError as e:
        raise _http(e) from None


@router.post("/sessions/{session_id}/advance", response_model=SessionDetailOut)
def advance(
    session_id: str,
    req: AdvanceIn,
    provider: str = "synthetic",
    instrument_id: str = "SPY",
    svc: ReplayService = Depends(get_replay_service),
) -> SessionDetailOut:
    instrument = resolve_instrument(instrument_id, provider)
    try:
        return svc.advance(session_id, req, instrument)
    except ReplayError as e:
        raise _http(e) from None


@router.post("/sessions/{session_id}/back", response_model=SessionDetailOut)
def back(
    session_id: str,
    provider: str = "synthetic",
    instrument_id: str = "SPY",
    svc: ReplayService = Depends(get_replay_service),
) -> SessionDetailOut:
    instrument = resolve_instrument(instrument_id, provider)
    try:
        return svc.back(session_id, instrument)
    except ReplayError as e:
        raise _http(e) from None


@router.post("/sessions/{session_id}/judgments", response_model=JudgmentOut, status_code=201)
def submit_judgment(
    session_id: str,
    req: JudgmentIn,
    provider: str = "synthetic",
    instrument_id: str = "SPY",
    svc: ReplayService = Depends(get_replay_service),
) -> JudgmentOut:
    """Predict First：提交即锁定（无更新接口）。bar_index 取服务端 cursor。"""
    instrument = resolve_instrument(instrument_id, provider)
    try:
        j = svc.submit_judgment(session_id, req, instrument)
        return JudgmentOut(
            id=j.id, session_id=j.session_id, bar_index=j.bar_index,
            bar_time_utc=j.bar_time_utc, payload=j.payload, submitted_at=j.submitted_at,
        )
    except ReplayError as e:
        raise _http(e) from None


@router.get("/sessions/{session_id}/judgments", response_model=list[JudgmentOut])
def list_judgments(
    session_id: str,
    provider: str = "synthetic",
    instrument_id: str = "SPY",
    svc: ReplayService = Depends(get_replay_service),
) -> list[JudgmentOut]:
    instrument = resolve_instrument(instrument_id, provider)
    try:
        svc.get(session_id, instrument)  # 校验存在
    except ReplayError as e:
        raise _http(e) from None
    return [
        JudgmentOut(
            id=j.id, session_id=j.session_id, bar_index=j.bar_index,
            bar_time_utc=j.bar_time_utc, payload=j.payload, submitted_at=j.submitted_at,
        )
        for j in svc._repo.list_judgments(session_id)
    ]


@router.delete("/sessions/{session_id}/judgments/{judgment_id}")
def delete_judgment(
    session_id: str,
    judgment_id: int,
    request: Request,
    provider: str = "synthetic",
    instrument_id: str = "SPY",
    svc: ReplayService = Depends(get_replay_service),
) -> dict:
    """删除指定判断记录，并级联清理对应的 AI 复盘缓存。"""
    _ = resolve_instrument(instrument_id, provider)
    try:
        svc.delete_judgment(session_id, judgment_id)
        coach_svc = getattr(request.app.state, "ai_coach_service", None)
        if coach_svc and hasattr(coach_svc, "evict_review"):
            coach_svc.evict_review(session_id, judgment_id)
        return {"status": "ok", "deleted_judgment_id": judgment_id}
    except ReplayError as e:
        raise _http(e) from None


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: str,
    request: Request,
    provider: str = "synthetic",
    instrument_id: str = "SPY",
    svc: ReplayService = Depends(get_replay_service),
) -> dict:
    """删除整场回放会话（外键级联清空全部关联判断、模拟交易与笔记）。"""
    _ = resolve_instrument(instrument_id, provider)
    try:
        svc.delete_session(session_id)
        coach_svc = getattr(request.app.state, "ai_coach_service", None)
        if coach_svc and hasattr(coach_svc, "evict_session"):
            coach_svc.evict_session(session_id)
        return {"status": "ok", "deleted_session_id": session_id}
    except ReplayError as e:
        raise _http(e) from None


@router.post("/sessions/{session_id}/annotations", response_model=AnnotationOut, status_code=201)
def add_annotation(
    session_id: str,
    req: AnnotationIn,
    provider: str = "synthetic",
    instrument_id: str = "SPY",
    svc: ReplayService = Depends(get_replay_service),
) -> AnnotationOut:
    instrument = resolve_instrument(instrument_id, provider)
    try:
        a = svc.add_annotation(session_id, req, instrument)
    except ReplayError as e:
        raise _http(e) from None
    return AnnotationOut(
        id=a.id, session_id=a.session_id, bar_index=a.bar_index, bar_time_utc=a.bar_time_utc,
        kind=a.kind, label=a.label, text=a.text, created_at=a.created_at, updated_at=a.updated_at,
    )


@router.get("/sessions/{session_id}/annotations", response_model=list[AnnotationOut])
def list_annotations(
    session_id: str,
    provider: str = "synthetic",
    instrument_id: str = "SPY",
    svc: ReplayService = Depends(get_replay_service),
) -> list[AnnotationOut]:
    instrument = resolve_instrument(instrument_id, provider)
    try:
        svc.get(session_id, instrument)
    except ReplayError as e:
        raise _http(e) from None
    return [
        AnnotationOut(
            id=a.id, session_id=a.session_id, bar_index=a.bar_index, bar_time_utc=a.bar_time_utc,
            kind=a.kind, label=a.label, text=a.text, created_at=a.created_at, updated_at=a.updated_at,
        )
        for a in svc._repo.list_annotations(session_id)
    ]
