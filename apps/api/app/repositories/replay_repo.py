"""回放会话/判断/标注 的数据访问（SQLite）。"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models.orm import AnnotationORM, JudgmentORM, ReplaySessionORM


class ReplayRepository:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def create_session(
        self,
        *,
        instrument_id: str,
        provider: str,
        day: date,
        timeframe: str,
        mode: str,
        warmup_bars: int,
    ) -> ReplaySessionORM:
        with self._factory() as s:
            orm = ReplaySessionORM(
                id=uuid.uuid4().hex,
                instrument_id=instrument_id,
                provider=provider,
                day=day,
                timeframe=timeframe,
                mode=mode,
                warmup_bars=warmup_bars,
                cursor_index=warmup_bars,
                state="running",
                sampling_mode="user_initiated",
            )
            s.add(orm)
            s.commit()
            s.refresh(orm)
            return orm

    def get(self, session_id: str) -> ReplaySessionORM | None:
        with self._factory() as s:
            orm = s.get(ReplaySessionORM, session_id)
            if orm is not None:
                s.expunge(orm)
            return orm

    def list_sessions(self, limit: int = 100) -> list[ReplaySessionORM]:
        """列出最近的回放会话（倒序），供前端会话管理面板展示。"""
        with self._factory() as s:
            rows = s.scalars(
                select(ReplaySessionORM).order_by(ReplaySessionORM.created_at.desc()).limit(limit)
            ).all()
            for r in rows:
                s.expunge(r)
            return list(rows)

    def update(self, orm: ReplaySessionORM) -> None:
        with self._factory() as s:
            s.merge(orm)
            s.commit()

    def add_judgment(
        self, session_id: str, bar_index: int, bar_time_utc: datetime, payload: dict
    ) -> JudgmentORM:
        with self._factory() as s:
            orm = JudgmentORM(
                session_id=session_id, bar_index=bar_index, bar_time_utc=bar_time_utc, payload=payload
            )
            s.add(orm)
            s.commit()
            s.refresh(orm)
            s.expunge(orm)
            return orm

    def list_judgments(self, session_id: str) -> list[JudgmentORM]:
        with self._factory() as s:
            rows = s.scalars(
                select(JudgmentORM).where(JudgmentORM.session_id == session_id).order_by(JudgmentORM.id)
            ).all()
            for r in rows:
                s.expunge(r)
            return list(rows)

    def delete_judgment(self, session_id: str, judgment_id: int) -> bool:
        with self._factory() as s:
            orm = s.get(JudgmentORM, judgment_id)
            if orm is None or orm.session_id != session_id:
                return False
            s.delete(orm)
            s.commit()
            return True

    def delete_session(self, session_id: str) -> bool:
        with self._factory() as s:
            orm = s.get(ReplaySessionORM, session_id)
            if orm is None:
                return False
            s.delete(orm)
            s.commit()
            return True

    def add_annotation(
        self,
        session_id: str,
        bar_index: int,
        bar_time_utc: datetime,
        kind: str,
        label: str | None,
        text: str | None,
    ) -> AnnotationORM:
        with self._factory() as s:
            orm = AnnotationORM(
                session_id=session_id,
                bar_index=bar_index,
                bar_time_utc=bar_time_utc,
                kind=kind,
                label=label,
                text=text,
            )
            s.add(orm)
            s.commit()
            s.refresh(orm)
            s.expunge(orm)
            return orm

    def list_annotations(self, session_id: str) -> list[AnnotationORM]:
        with self._factory() as s:
            rows = s.scalars(
                select(AnnotationORM).where(AnnotationORM.session_id == session_id).order_by(AnnotationORM.id)
            ).all()
            for r in rows:
                s.expunge(r)
            return list(rows)
