"""AI Coach API 路由。服务实例由应用工厂注入到 app.state。"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse

from app.core.config import Settings
from app.domain.bar import SessionType, Timeframe
from app.domain.instrument import get_instrument
from app.replay.service import ReplayError
from app.services.ai_coach_service import AICoachService, CoachAnswer
from app.services.decision_review_service import DecisionContextExtractor

router = APIRouter(prefix="/coach", tags=["coach"])


def _coach(request: Request) -> AICoachService:
    return request.app.state.ai_coach_service


def _extractor(request: Request) -> DecisionContextExtractor:
    return request.app.state.decision_context_extractor


def _review_error(error: ReplayError) -> HTTPException:
    return HTTPException(error.status, detail={"code": error.code, "message": error.message})


@router.get("/status")
def coach_status(request: Request) -> dict:
    return {"enabled": _coach(request).enabled}


@router.get("/config")
def coach_config(request: Request) -> dict:
    return _coach(request).config()


@router.get("/concept")
def ask_concept(
    request: Request,
    term: str = Query(..., min_length=1),
    question: str = Query("", max_length=500),
) -> CoachAnswer:
    if not term.strip():
        raise HTTPException(400, "概念术语不能为空")
    return _coach(request).ask_concept(term, question)


@router.post("/sessions/{session_id}/judgments/{judgment_id}/review")
def review_judgment(
    request: Request,
    session_id: str,
    judgment_id: int,
    refresh: bool = Query(False, description="是否强制重新调用 AI 分析"),
) -> dict:
    try:
        context = _extractor(request).extract(session_id, judgment_id)
    except ReplayError as error:
        raise _review_error(error) from None
    ans = _coach(request).review_decision(context, force_refresh=refresh)
    enriched_refs: list[dict] = []
    for r in ans.references:
        ref_item = dict(r)
        page = ref_item.get("pdf_page")
        if page and int(page) > 0:
            book = ref_item.get("book", "")
            src = ref_item.get("source_file", "")
            ref_item["image_url"] = f"/api/v1/knowledge/page-image?pdf_page={page}&book={book}&source_file={src}"
        enriched_refs.append(ref_item)
    return {
        "source_grounded": ans.source_grounded,
        "mechanical_approx": ans.mechanical_approx,
        "coach_interpretation": ans.coach_interpretation,
        "references": enriched_refs,
        "insufficient_evidence": ans.insufficient_evidence,
    }


@router.get("/sessions/{session_id}/judgments/{judgment_id}/analogs")
def analogs(request: Request, session_id: str, judgment_id: int) -> dict:
    try:
        replay = request.app.state.replay_service
        session = replay._repo.get(session_id)
        if session is None:
            raise ReplayError("not_found", "session 不存在", 404)
        context = _extractor(request).extract(session_id, judgment_id)
        instrument = get_instrument(session.instrument_id, session.provider)
        data = replay._load(instrument, session.day, context_days=0)
        query = data.rth_bars[: context["bar_index"] + 1]
        history = request.app.state.store.read_bars(
            instrument, Timeframe.M5, date(2000, 1, 1), date.today()
        )
        history = [bar for bar in history if bar.session == SessionType.RTH]
        matches = request.app.state.analog_search_service.search(
            query, history_bars=history, top_k=3
        )
        return {"session_id": session_id, "judgment_id": judgment_id, "matches": [asdict(m) for m in matches]}
    except ReplayError as error:
        raise _review_error(error) from None


@router.get("/analogs/chart-image")
def get_analog_chart_image(request: Request, file: str = Query(...)) -> FileResponse:
    """提供历史 SPY 相似走势的 K 线切片图像文件。"""
    settings: Settings = getattr(request.app.state, "settings", Settings())
    target = settings.data_dir / "cache" / "analog_charts" / Path(file).name
    if not target.is_file():
        raise HTTPException(404, "未找到指定的相似走势图表图片")
    return FileResponse(str(target), media_type="image/png")


@router.post("/sessions/{session_id}/summary-review")
def summary_review(request: Request, session_id: str) -> dict:
    try:
        # Each context is independently bounded at its own judgment; no later cursor
        # or posterior trade outcome is included in the prompts.
        extractor = _extractor(request)
        replay = request.app.state.replay_service
        if replay._repo.get(session_id) is None:
            raise ReplayError("not_found", "session 不存在", 404)
        contexts = [extractor.extract(session_id, j.id) for j in replay._repo.list_judgments(session_id)]
    except ReplayError as error:
        raise _review_error(error) from None
    result = _coach(request).summary_review(contexts)
    return {"session_id": session_id, **result}
