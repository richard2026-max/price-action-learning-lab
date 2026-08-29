"""回放路由（MVP-A 核心）。所有行情响应经 ReplayService 服务端裁剪。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.deps import get_current_user, get_replay_service, resolve_instrument
from app.models.orm import UserORM
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


def _http(error: ReplayError) -> HTTPException:
    return HTTPException(
        status_code=error.status,
        detail={"code": error.code, "message": error.message},
    )


@router.get("/days")
def available_days(
    instrument_id: str = "SPY",
    provider: str = "synthetic",
    include_sealed: bool = Query(False, description="是否包含封存考试日"),
    svc: ReplayService = Depends(get_replay_service),
    _user: UserORM = Depends(get_current_user),
) -> dict:
    instrument = resolve_instrument(instrument_id, provider)
    return {"days": svc.available_days(instrument, include_sealed=include_sealed)}


@router.get("/exam-summary")
def exam_summary(
    instrument_id: str = "SPY",
    provider: str = "synthetic",
    svc: ReplayService = Depends(get_replay_service),
    _user: UserORM = Depends(get_current_user),
) -> dict:
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
    _user: UserORM = Depends(get_current_user),
) -> dict:
    instrument = resolve_instrument(instrument_id, provider)
    try:
        return {"day": svc.random_day(instrument, seed, for_exam=for_exam)}
    except ReplayError as error:
        raise _http(error) from None


@router.post("/sessions", response_model=SessionDetailOut)
def create_session(
    req: CreateSessionIn,
    svc: ReplayService = Depends(get_replay_service),
    user: UserORM = Depends(get_current_user),
) -> SessionDetailOut:
    instrument = resolve_instrument(req.instrument_id, req.provider)
    try:
        return svc.create(req, instrument, user.id)
    except ReplayError as error:
        raise _http(error) from None


@router.get("/sessions")
def list_sessions(
    limit: int = Query(100, ge=1, le=500),
    svc: ReplayService = Depends(get_replay_service),
    user: UserORM = Depends(get_current_user),
) -> list[dict]:
    out: list[dict] = []
    for orm in svc._repo.list_sessions(user.id, limit=limit):
        judgments = svc._repo.list_judgments(orm.id, user.id)
        out.append(
            {
                "session_id": orm.id,
                "day": orm.day.isoformat(),
                "provider": orm.provider,
                "instrument_id": orm.instrument_id,
                "mode": orm.mode,
                "state": orm.state,
                "cursor_index": orm.cursor_index,
                "cursor_version": orm.cursor_version,
                "judgment_count": len(judgments),
                "created_at": orm.created_at.isoformat(),
            }
        )
    return out


@router.get("/sessions/{session_id}", response_model=SessionDetailOut)
def get_session(
    session_id: str,
    provider: str = "synthetic",
    instrument_id: str = "SPY",
    svc: ReplayService = Depends(get_replay_service),
    user: UserORM = Depends(get_current_user),
) -> SessionDetailOut:
    instrument = resolve_instrument(instrument_id, provider)
    try:
        return svc.get(session_id, instrument, user.id)
    except ReplayError as error:
        raise _http(error) from None


@router.post("/sessions/{session_id}/advance", response_model=SessionDetailOut)
def advance(
    session_id: str,
    req: AdvanceIn,
    provider: str = "synthetic",
    instrument_id: str = "SPY",
    svc: ReplayService = Depends(get_replay_service),
    user: UserORM = Depends(get_current_user),
) -> SessionDetailOut:
    instrument = resolve_instrument(instrument_id, provider)
    try:
        return svc.advance(session_id, req, instrument, user.id)
    except ReplayError as error:
        raise _http(error) from None


@router.post("/sessions/{session_id}/back", response_model=SessionDetailOut)
def back(
    session_id: str,
    provider: str = "synthetic",
    instrument_id: str = "SPY",
    svc: ReplayService = Depends(get_replay_service),
    user: UserORM = Depends(get_current_user),
) -> SessionDetailOut:
    instrument = resolve_instrument(instrument_id, provider)
    try:
        return svc.back(session_id, instrument, user.id)
    except ReplayError as error:
        raise _http(error) from None


@router.post("/sessions/{session_id}/judgments", response_model=JudgmentOut, status_code=201)
def submit_judgment(
    session_id: str,
    req: JudgmentIn,
    provider: str = "synthetic",
    instrument_id: str = "SPY",
    svc: ReplayService = Depends(get_replay_service),
    user: UserORM = Depends(get_current_user),
) -> JudgmentOut:
    instrument = resolve_instrument(instrument_id, provider)
    try:
        judgment = svc.submit_judgment(session_id, req, instrument, user.id)
        return JudgmentOut(
            id=judgment.id,
            session_id=judgment.session_id,
            bar_index=judgment.bar_index,
            bar_time_utc=judgment.bar_time_utc,
            payload=judgment.payload,
            submitted_at=judgment.submitted_at,
        )
    except ReplayError as error:
        raise _http(error) from None


@router.get("/sessions/{session_id}/judgments", response_model=list[JudgmentOut])
def list_judgments(
    session_id: str,
    provider: str = "synthetic",
    instrument_id: str = "SPY",
    svc: ReplayService = Depends(get_replay_service),
    user: UserORM = Depends(get_current_user),
) -> list[JudgmentOut]:
    instrument = resolve_instrument(instrument_id, provider)
    try:
        svc.get(session_id, instrument, user.id)
    except ReplayError as error:
        raise _http(error) from None
    return [
        JudgmentOut(
            id=item.id,
            session_id=item.session_id,
            bar_index=item.bar_index,
            bar_time_utc=item.bar_time_utc,
            payload=item.payload,
            submitted_at=item.submitted_at,
        )
        for item in svc._repo.list_judgments(session_id, user.id)
    ]


@router.delete("/sessions/{session_id}/judgments/{judgment_id}")
def delete_judgment(
    session_id: str,
    judgment_id: int,
    request: Request,
    provider: str = "synthetic",
    instrument_id: str = "SPY",
    svc: ReplayService = Depends(get_replay_service),
    user: UserORM = Depends(get_current_user),
) -> dict:
    _ = resolve_instrument(instrument_id, provider)
    try:
        svc.delete_judgment(session_id, judgment_id, user.id)
        coach_svc = getattr(request.app.state, "ai_coach_service", None)
        if coach_svc and hasattr(coach_svc, "evict_review"):
            coach_svc.evict_review(session_id, judgment_id)
        return {"status": "ok", "deleted_judgment_id": judgment_id}
    except ReplayError as error:
        raise _http(error) from None


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: str,
    request: Request,
    provider: str = "synthetic",
    instrument_id: str = "SPY",
    svc: ReplayService = Depends(get_replay_service),
    user: UserORM = Depends(get_current_user),
) -> dict:
    _ = resolve_instrument(instrument_id, provider)
    try:
        svc.delete_session(session_id, user.id)
        coach_svc = getattr(request.app.state, "ai_coach_service", None)
        if coach_svc and hasattr(coach_svc, "evict_session"):
            coach_svc.evict_session(session_id)
        return {"status": "ok", "deleted_session_id": session_id}
    except ReplayError as error:
        raise _http(error) from None


@router.post("/sessions/{session_id}/annotations", response_model=AnnotationOut, status_code=201)
def add_annotation(
    session_id: str,
    req: AnnotationIn,
    provider: str = "synthetic",
    instrument_id: str = "SPY",
    svc: ReplayService = Depends(get_replay_service),
    user: UserORM = Depends(get_current_user),
) -> AnnotationOut:
    instrument = resolve_instrument(instrument_id, provider)
    try:
        annotation = svc.add_annotation(session_id, req, instrument, user.id)
    except ReplayError as error:
        raise _http(error) from None
    return AnnotationOut(
        id=annotation.id,
        session_id=annotation.session_id,
        bar_index=annotation.bar_index,
        bar_time_utc=annotation.bar_time_utc,
        kind=annotation.kind,
        label=annotation.label,
        text=annotation.text,
        created_at=annotation.created_at,
        updated_at=annotation.updated_at,
    )


@router.get("/sessions/{session_id}/annotations", response_model=list[AnnotationOut])
def list_annotations(
    session_id: str,
    provider: str = "synthetic",
    instrument_id: str = "SPY",
    svc: ReplayService = Depends(get_replay_service),
    user: UserORM = Depends(get_current_user),
) -> list[AnnotationOut]:
    instrument = resolve_instrument(instrument_id, provider)
    try:
        svc.get(session_id, instrument, user.id)
    except ReplayError as error:
        raise _http(error) from None
    return [
        AnnotationOut(
            id=item.id,
            session_id=item.session_id,
            bar_index=item.bar_index,
            bar_time_utc=item.bar_time_utc,
            kind=item.kind,
            label=item.label,
            text=item.text,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in svc._repo.list_annotations(session_id, user.id)
    ]
