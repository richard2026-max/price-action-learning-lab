"""知识库检索 API 路由与课件原书页面图像渲染。"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse

from app.api.deps import get_current_user
from app.core.config import Settings
from app.models.orm import UserORM
from app.services.knowledge_service import KnowledgeChunk, KnowledgeService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

_service = KnowledgeService()


def _get_service(request: Request) -> KnowledgeService:
    if hasattr(request.app.state, "knowledge_service"):
        return request.app.state.knowledge_service
    return _service


def _resolve_pdf(settings: Settings, book: str | None, pdf_page: int, source_file: str | None) -> Path | None:
    if source_file:
        p = Path(source_file)
        if p.is_file() and p.suffix.lower() == ".pdf":
            return p
        for directory in (settings.courseware_dir, settings.books_dir):
            candidate = directory / p.name
            if candidate.is_file() and candidate.suffix.lower() == ".pdf":
                return candidate

    code = (book or "").upper()
    if code in ("T", "TRENDS"):
        candidates = list(settings.books_dir.glob("*Trends*.pdf"))
        if candidates:
            return candidates[0]
    if code in ("R", "RANGES"):
        candidates = list(settings.books_dir.glob("*Ranges*.pdf"))
        if candidates:
            return candidates[0]
    if code in ("REV", "REVERSALS"):
        candidates = list(settings.books_dir.glob("*Reversals*.pdf"))
        if candidates:
            return candidates[0]
    if code in ("COURSE", "COURSEWARE"):
        base_candidates = list(settings.courseware_dir.glob("*基础篇*.pdf"))
        adv_candidates = list(settings.courseware_dir.glob("*进阶篇*.pdf"))
        if base_candidates and pdf_page <= 2819:
            return base_candidates[0]
        if adv_candidates:
            return adv_candidates[0]

    for directory in (settings.courseware_dir, settings.books_dir):
        if not directory.is_dir():
            continue
        for f in sorted(directory.glob("*.pdf")):
            return f
    return None


@router.get("/page-image")
def get_page_image(
    request: Request,
    pdf_page: int = Query(..., ge=1, description="PDF 页码（从 1 开始）"),
    book: str | None = Query(None, description="书籍或课件代号：T, R, REV, COURSE, BOOK"),
    source_file: str | None = Query(None, description="来源文件名或文件路径"),
    scale: float = Query(1.5, ge=0.5, le=3.0, description="渲染缩放比例"),
    _user: UserORM = Depends(get_current_user),
) -> FileResponse:
    """渲染指定原书或课件 PDF 页面为高清晰度 JPEG 图片（支持磁盘缓存）。"""
    settings: Settings = getattr(request.app.state, "settings", Settings())
    target_pdf = _resolve_pdf(settings, book, pdf_page, source_file)
    if not target_pdf or not target_pdf.is_file():
        raise HTTPException(404, "未找到对应的课件或原书 PDF 文件")

    cache_dir = settings.data_dir / "cache" / "page_images"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{target_pdf.stem}_{pdf_page}_{int(scale * 10)}.jpg"
    if cache_file.is_file() and cache_file.stat().st_size > 0:
        return FileResponse(str(cache_file), media_type="image/jpeg")

    try:
        import pypdfium2 as pdfium

        doc = pdfium.PdfDocument(str(target_pdf))
        if pdf_page > len(doc):
            raise HTTPException(404, f"页码 {pdf_page} 超出文件总页数 {len(doc)}")
        page = doc[pdf_page - 1]
        image = page.render(scale=scale).to_pil()
        image.save(cache_file, "JPEG", quality=85)
        return FileResponse(str(cache_file), media_type="image/jpeg")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"渲染 PDF 页面图像失败: {e}") from None


@router.get("/search")
def search_knowledge(
    request: Request,
    q: str = Query(..., min_length=1, description="检索关键词（支持多词空格分隔）"),
    books: str | None = Query(None, description="限定书籍代号，逗号分隔：T,R,REV"),
    max_results: int = Query(10, ge=1, le=50),
    _user: UserORM = Depends(get_current_user),
) -> dict:
    svc = _get_service(request)
    books_list = [b.strip() for b in books.split(",")] if books else None
    results: list[KnowledgeChunk] = svc.search(q, books=books_list, max_results=max_results)
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
    request: Request,
    term: str,
    max_results: int = Query(5, ge=1, le=20),
    _user: UserORM = Depends(get_current_user),
) -> dict:
    """按 Concept Spec 英文术语名检索原书相关章节。"""
    svc = _get_service(request)
    results: list[KnowledgeChunk] = svc.search(term, max_results=max_results)
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

