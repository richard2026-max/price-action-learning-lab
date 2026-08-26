"""KnowledgeService 的本地来源与增量缓存测试。"""

from __future__ import annotations

import json
from pathlib import Path

from app.core.config import Settings
from app.services import knowledge_service as knowledge_module
from app.services.knowledge_service import KnowledgeService


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        books_dir=tmp_path / "books",
        courseware_dir=tmp_path / "courseware",
        knowledge_cache_path=tmp_path / "cache" / "knowledge_index.json",
    )


def test_sources_are_indexed_and_cache_is_reused(tmp_path, monkeypatch):
    monkeypatch.setattr(knowledge_module, "BOOK_MAP", {})
    books = tmp_path / "books"
    courseware = tmp_path / "courseware"
    books.mkdir()
    courseware.mkdir()
    (books / "notes.md").write_text("Trend bars and pullbacks are important objective facts.\n", encoding="utf-8")
    (courseware / "课件.txt").write_text(
        "A second entry is often a higher probability setup in context.\n", encoding="utf-8"
    )

    settings = _settings(tmp_path)
    first = KnowledgeService(settings)
    stats = first.index_stats()
    assert stats["by_source_type"] == {"notes": 1, "courseware": 1}
    assert first.search("pullbacks", max_results=1)[0].source_type == "notes"
    assert first.search("second entry", max_results=1)[0].source_file.endswith("课件.txt")

    cache = json.loads(settings.knowledge_cache_path.read_text(encoding="utf-8"))
    assert set(cache) == {str(books / "notes.md"), str(courseware / "课件.txt")}
    assert cache[str(courseware / "课件.txt")]["source_type"] == "courseware"

    second = KnowledgeService(settings)
    called = False
    original = second._parse_file

    def fail_if_reparsed(*args, **kwargs):
        nonlocal called
        called = True
        return original(*args, **kwargs)

    monkeypatch.setattr(second, "_parse_file", fail_if_reparsed)
    assert second.index_stats()["total_chunks"] == 2
    assert not called


def test_changed_added_and_deleted_files_update_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(knowledge_module, "BOOK_MAP", {})
    courseware = tmp_path / "courseware"
    courseware.mkdir()
    source = courseware / "lesson.txt"
    source.write_text("Initial lesson about breakouts and signal bars.\n", encoding="utf-8")
    settings = _settings(tmp_path)

    assert KnowledgeService(settings).search("breakouts", max_results=1)
    source.write_text("Updated lesson about wedges and reversals.\n", encoding="utf-8")
    updated = KnowledgeService(settings)
    assert updated.search("breakouts", max_results=1) == []
    assert updated.search("wedges", max_results=1)

    added = courseware / "new.md"
    added.write_text("New lesson about double bottoms and measured moves.\n", encoding="utf-8")
    with_added = KnowledgeService(settings)
    assert with_added.search("double bottoms", max_results=1)

    source.unlink()
    after_delete = KnowledgeService(settings)
    assert after_delete.search("wedges", max_results=1) == []
    manifest = json.loads(settings.knowledge_cache_path.read_text(encoding="utf-8"))
    assert str(source) not in manifest
    assert str(added) in manifest
