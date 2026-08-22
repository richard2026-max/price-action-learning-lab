"""AI Coach API 路由。默认禁用，需在 Settings 中启用。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.services.ai_coach_service import AICoachService, CoachAnswer
from app.services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/coach", tags=["coach"])

_coach: AICoachService | None = None


def _get_coach() -> AICoachService:
    global _coach
    if _coach is None:
        from app.core.config import Settings

        settings = Settings()
        ks = KnowledgeService(data_dir=settings.data_dir)
        _coach = AICoachService(knowledge_svc=ks, llm_provider=None)
    return _coach


@router.get("/status")
def coach_status() -> dict:
    return {"enabled": _get_coach().enabled}


@router.get("/concept")
def ask_concept(
    term: str = Query(..., min_length=1),
    question: str = Query("", max_length=500),
) -> CoachAnswer:
    if not term.strip():
        raise HTTPException(400, "概念术语不能为空")
    return _get_coach().ask_concept(term, question)
