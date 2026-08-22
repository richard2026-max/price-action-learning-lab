"""知识库检索服务（Knowledge Retrieval Service）。

基于 data/knowledge/extracted/*.txt（带 PDFPAGE 标记）建立本地全文索引，
支持按关键词/概念名检索原书相关章节并返回结构化引用。
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import REPO_ROOT

BOOK_MAP = {
    "trends": {
        "code": "T",
        "file": "data/knowledge/extracted/trends.txt",
    },
    "ranges": {
        "code": "R",
        "file": "data/knowledge/extracted/ranges.txt",
    },
    "reversals": {
        "code": "REV",
        "file": "data/knowledge/extracted/reversals.txt",
    },
}


@dataclass(frozen=True, slots=True)
class KnowledgeChunk:
    book_code: str
    pdf_page: int
    print_page: str | None
    content: str
    chunk_id: str
    chunk_hash: str
    matched_terms: list[str] = field(default_factory=list)

    def to_ref(self) -> dict:
        return {
            "book": self.book_code,
            "pdf_page": self.pdf_page,
            "print_page": self.print_page,
            "chunk_id": self.chunk_id,
            "chunk_hash": self.chunk_hash,
        }


class KnowledgeService:
    """本地全文检索服务。惰性加载全部提取文本到内存。"""

    def __init__(self, data_dir: Path | None = None) -> None:
        self._chunks: list[dict] = []
        self._indexed = False
        self._data_dir = data_dir or (REPO_ROOT / "data")

    def _ensure_indexed(self) -> None:
        if self._indexed:
            return
        for key, meta in BOOK_MAP.items():
            path = REPO_ROOT / meta["file"]
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            pages = re.split(r"===== PDFPAGE (\d+) =====", text)
            for i in range(1, len(pages) - 1, 2):
                page_num = int(pages[i])
                content = pages[i + 1].strip()
                if len(content) < 20:
                    continue
                self._chunks.append({
                    "book_key": key,
                    "book_code": meta["code"],
                    "page": page_num,
                    "content": content,
                })
        self._indexed = True

    @staticmethod
    def _make_chunk_id(book: str, page: int, snippet: str) -> str:
        raw = f"{book}:{page}:{snippet[:80]}"
        return hashlib.blake2b(raw.encode(), digest_size=8).hexdigest()

    def search(
        self,
        query: str,
        books: list[str] | None = None,
        max_results: int = 10,
    ) -> list[KnowledgeChunk]:
        """按关键词搜索原书文本，返回按相关度排序的片段列表。"""
        self._ensure_indexed()
        if not query.strip():
            return []

        terms = [t.lower().strip() for t in re.split(r"[\s,;]+", query.lower()) if t.strip()]
        results: list[tuple[float, KnowledgeChunk]] = []

        for chunk in self._chunks:
            if books and chunk["book_key"] not in books:
                continue
            content_lower = chunk["content"].lower()
            score = 0.0
            matched: list[str] = []
            for term in terms:
                count = content_lower.count(term)
                if count > 0:
                    score += count * (len(term) / 10.0)
                    matched.append(term)

            if score <= 0:
                continue

            best_term = next(t for t in terms if t in content_lower)
            idx = content_lower.find(best_term)
            start = max(0, idx - 100)
            end = min(len(chunk["content"]), idx + 400)
            snippet = chunk["content"][start:end].strip()

            kc = KnowledgeChunk(
                book_code=chunk["book_code"],
                pdf_page=chunk["page"],
                print_page=None,
                content=snippet,
                chunk_id=self._make_chunk_id(chunk["book_code"], chunk["page"], snippet),
                chunk_hash=hashlib.blake2b(snippet.encode(), digest_size=8).hexdigest(),
                matched_terms=matched,
            )
            results.append((score, kc))

        results.sort(key=lambda x: -x[0])
        seen_pages: set[str] = set()
        deduped: list[KnowledgeChunk] = []
        for _, kc in results:
            key = f"{kc.book_code}:{kc.pdf_page}"
            if key in seen_pages:
                continue
            seen_pages.add(key)
            deduped.append(kc)
            if len(deduped) >= max_results:
                break
        return deduped

    def search_by_concept(self, concept_english_term: str, max_results: int = 5) -> list[KnowledgeChunk]:
        return self.search(concept_english_term, max_results=max_results)
