"""知识库检索 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.services.knowledge_service import KnowledgeChunk, KnowledgeService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

_service = KnowledgeService()


@router.get("/search")
def search_knowledge(
    q: str = Query(..., min_length=1, description="检索关键词（支持多词空格分隔）"),
    books: str | None = Query(None, description="限定书籍代号，逗号分隔：T,R,REV"),
    max_results: int = Query(10, ge=1, le=50),
) -> dict:
    books_list = [b.strip() for b in books.split(",")] if books else None
    results: list[KnowledgeChunk] = _service.search(q, books=books_list, max_results=max_results)
    return {
        "query": q,
        "total": len(results),
        "results": [
            {
                "book": kc.book_code,
                "pdf_page": kc.pdf_page,
                "print_page": kc.print_page,
                "snippet": kc.content[:400],
                "chunk_id": kc.chunk_id,
                "chunk_hash": kc.chunk_hash,
                "matched_terms": kc.matched_terms,
            }
            for kc in results
        ],
    }


@router.get("/concept/{term}")
def search_by_concept(
    term: str,
    max_results: int = Query(5, ge=1, le=20),
) -> dict:
    """按 Concept Spec 英文术语名检索原书相关章节。"""
    results: list[KnowledgeChunk] = _service.search(term, max_results=max_results)
    return {
        "concept_term": term,
        "total": len(results),
        "results": [
            {
                "book": kc.book_code,
                "pdf_page": kc.pdf_page,
                "print_page": kc.print_page,
                "snippet": kc.content[:400],
                "chunk_id": kc.chunk_id,
            }
            for kc in results
        ],
    }
