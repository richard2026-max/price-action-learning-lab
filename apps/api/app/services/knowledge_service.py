"""知识库检索服务（Knowledge Retrieval Service）。

负责将三类学习素材统一索引并支持增量热更新：
1. 原书提取文本（data/knowledge/extracted/*.txt，带 PDFPAGE 标记）—— 稳定内置来源；
2. 原书 PDF（AlBrooks书/*.pdf）—— 通过 pypdf 逐页提取文本层（含页码）；
3. 中文课件 PDF 与 Markdown 笔记（AlBrooks课件/*）—— 通过 pypdf / 直接文本解析。

增量缓存策略：
- 记录每个文件的 mtime + 内容 hash 到 data/cache/knowledge_index.json；
- 启动/调用时扫描，文件未变 -> 读内存缓存（毫秒级）；新增/变化 -> 自动解析增量合并；
- 保证"新课件丢进目录即自动更新"，无须手动重建。

来源标记：source_type ∈ {book_extract, book_pdf, courseware, notes}；
content-provenance-policy §五：print_page 仅确定时填写否则 null，禁止编造页码。
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import REPO_ROOT, Settings

BOOK_MAP = {
    "trends": {"code": "T", "file": "data/knowledge/extracted/trends.txt"},
    "ranges": {"code": "R", "file": "data/knowledge/extracted/ranges.txt"},
    "reversals": {"code": "REV", "file": "data/knowledge/extracted/reversals.txt"},
}

_SUPPORTED_EXT = {".pdf", ".md", ".txt"}


@dataclass(frozen=True, slots=True)
class KnowledgeChunk:
    book_code: str          # 书籍代号(T/R/REV) 或来源代称(COURSE/NOTE)
    pdf_page: int           # PDF 页码（txt 切片用段内页码，md 无页码用 0）
    print_page: str | None  # 印刷页码（仅确定时填写）
    content: str
    chunk_id: str
    chunk_hash: str
    matched_terms: list[str] = field(default_factory=list)
    source_type: str = "book_extract"  # book_extract | book_pdf | courseware | notes
    source_file: str = ""

    def to_ref(self) -> dict:
        return {
            "book": self.book_code,
            "pdf_page": self.pdf_page,
            "print_page": self.print_page,
            "chunk_id": self.chunk_id,
            "chunk_hash": self.chunk_hash,
            "source_type": self.source_type,
            "source_file": self.source_file,
        }


class KnowledgeService:
    """本地全文检索服务。惰性加载、增量热更新（mtime + hash 缓存）。"""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        data_dir: Path | None = None,
    ) -> None:
        """Create the service.

        ``data_dir`` is retained as a compatibility keyword for older callers
        (notably the coach status route). New code should pass ``Settings`` so
        books/courseware/cache paths remain configurable independently.
        """
        if settings is not None and data_dir is not None:
            raise ValueError("pass either settings or data_dir, not both")
        self._settings = settings or (
            Settings(
                data_dir=data_dir,
                knowledge_cache_path=data_dir / "cache" / "knowledge_index.json",
            )
            if data_dir is not None
            else Settings()
        )
        self._chunks: list[dict] = []
        self._indexed = False

    def _ensure_indexed(self) -> None:
        if self._indexed:
            return
        self._load_cache()
        self._indexed = True

    def _cache_path(self) -> Path:
        return self._settings.knowledge_cache_path

    def _load_cache(self) -> None:
        """扫描所有来源，合并内置 + 新增/变更文件，写入缓存索引。"""
        self._chunks = []
        # 1) 内置原书提取文本（优先加载，作为稳定权威）
        self._index_book_extracts()

        # 2) 目录来源（原书 PDF + 课件 PDF/MD），增量热更新
        index_manifest: dict[str, dict] = {}
        if self._cache_path().is_file():
            try:
                index_manifest = json.loads(self._cache_path().read_text(encoding="utf-8"))
            except Exception:
                index_manifest = {}

        scanned = self._scan_dir(self._settings.books_dir, "book_pdf")
        scanned.update(self._scan_dir(self._settings.courseware_dir, "courseware"))

        changed_files: list[tuple[Path, str]] = []
        for fpath_str, meta in scanned.items():
            fpath = Path(fpath_str)
            mtime = meta["mtime"]
            fhash = meta["hash"]
            stype = meta["source_type"]
            prev = index_manifest.get(str(fpath))
            if prev and prev.get("hash") == fhash and prev.get("mtime") == mtime:
                self._chunks.extend(prev.get("chunks", []))
            else:
                changed_files.append((fpath, stype))

        for fpath, stype in changed_files:
            chunks = self._parse_file(fpath, default_source_type=stype)
            self._chunks.extend(chunks)
            index_manifest[str(fpath)] = {
                "hash": scanned[str(fpath)]["hash"],
                "mtime": scanned[str(fpath)]["mtime"],
                "source_type": stype,
                "chunks": chunks,
            }

        for stale in [k for k in index_manifest if not Path(k).is_file()]:
            del index_manifest[stale]

        self._cache_path().parent.mkdir(parents=True, exist_ok=True)
        self._cache_path().write_text(json.dumps(index_manifest, ensure_ascii=False, indent=1), encoding="utf-8")

    @staticmethod
    def _scan_dir(directory: Path, source_type: str) -> dict[str, dict]:
        result: dict[str, dict] = {}
        if not directory.is_dir():
            return result
        for f in directory.iterdir():
            if f.is_file() and f.suffix.lower() in _SUPPORTED_EXT:
                fhash = _file_hash(f)
                result[str(f)] = {
                    "mtime": int(f.stat().st_mtime),
                    "hash": fhash,
                    "source_type": source_type,
                }
        return result

    def _index_book_extracts(self) -> None:
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
                    "source_type": "book_extract",
                    "source_file": str(path),
                })

    def _parse_file(self, path: Path, default_source_type: str) -> list[dict]:
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return self._parse_pdf(path, source_type=default_source_type)
        if suffix == ".md":
            stype = "notes" if "笔记" in path.name or "note" in path.name.lower() else default_source_type
            return self._parse_text(path, source_type=stype)
        if suffix == ".txt":
            return self._parse_text(path, source_type=default_source_type)
        return []

    @staticmethod
    def _parse_pdf(path: Path, source_type: str) -> list[dict]:
        try:
            import pypdf
        except ImportError:
            return []
        chunks: list[dict] = []
        code = "COURSE" if source_type == "courseware" else "BOOK"
        try:
            reader = pypdf.PdfReader(str(path))
            for page_no, page in enumerate(reader.pages, start=1):
                try:
                    text = page.extract_text() or ""
                except Exception:
                    text = ""
                text = " ".join(text.split())
                if len(text) < 20:
                    continue
                chunks.append({
                    "book_key": "courseware" if source_type == "courseware" else "books",
                    "book_code": code,
                    "page": page_no,
                    "content": text[:2000],
                    "source_type": source_type,
                    "source_file": str(path),
                })
        except Exception:
            return []
        return chunks

    @staticmethod
    def _parse_text(path: Path, source_type: str) -> list[dict]:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            try:
                text = path.read_text(encoding="gbk")
            except Exception:
                return []
        chunks: list[dict] = []
        step = 1500
        code = "NOTE" if source_type == "notes" else "COURSE"
        for i in range(0, max(1, len(text)), step):
            content = text[i : i + step].strip()
            if len(content) < 20:
                continue
            chunks.append({
                "book_key": source_type,
                "book_code": code,
                "page": 0,
                "content": content,
                "source_type": source_type,
                "source_file": str(path),
            })
        return chunks

    @staticmethod
    def _make_chunk_id(book: str, page: int, snippet: str) -> str:
        raw = f"{book}:{page}:{snippet[:80]}"
        return hashlib.blake2b(raw.encode(), digest_size=8).hexdigest()

    def search(
        self,
        query: str,
        books: list[str] | None = None,
        max_results: int = 10,
        source_type: str | None = None,
    ) -> list[KnowledgeChunk]:
        self._ensure_indexed()
        if not query.strip():
            return []

        terms = [t.lower().strip() for t in re.split(r"[\s,;]+", query.lower()) if t.strip()]
        results: list[tuple[float, KnowledgeChunk]] = []

        for chunk in self._chunks:
            if books and chunk.get("book_key") not in books:
                continue
            if source_type and chunk.get("source_type") != source_type:
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
            start = max(0, idx - 120)
            end = min(len(chunk["content"]), idx + 400)
            snippet = chunk["content"][start:end].strip()

            kc = KnowledgeChunk(
                book_code=chunk.get("book_code", "COURSE"),
                pdf_page=chunk.get("page", 0),
                print_page=None,
                content=snippet,
                chunk_id=self._make_chunk_id(chunk.get("book_code", "COURSE"), chunk.get("page", 0), snippet),
                chunk_hash=hashlib.blake2b(snippet.encode(), digest_size=8).hexdigest(),
                matched_terms=matched,
                source_type=chunk.get("source_type", "book_extract"),
                source_file=chunk.get("source_file", ""),
            )
            results.append((score, kc))

        results.sort(key=lambda x: -x[0])
        seen: set[str] = set()
        deduped: list[KnowledgeChunk] = []
        for _, kc in results:
            key = f"{kc.source_file}:{kc.pdf_page}"
            if key in seen:
                continue
            seen.add(key)
            deduped.append(kc)
            if len(deduped) >= max_results:
                break
        return deduped

    def search_by_concept(self, concept_english_term: str, max_results: int = 5) -> list[KnowledgeChunk]:
        return self.search(concept_english_term, max_results=max_results)

    def index_stats(self) -> dict:
        self._ensure_indexed()
        from collections import Counter
        by_source = Counter(c.get("source_type", "book_extract") for c in self._chunks)
        return {
            "total_chunks": len(self._chunks),
            "by_source_type": dict(by_source),
            "cache_path": str(self._cache_path()),
        }


def _file_hash(path: Path) -> str:
    h = hashlib.blake2b()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 16), b""):
            h.update(c)
    return h.hexdigest()
