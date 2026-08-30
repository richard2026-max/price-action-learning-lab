"""用户隔离的回放会话、判断与标注数据访问。"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.models.orm import (
    AnnotationORM,
    JudgmentORM,
    ReplayAdvanceRequestORM,
    ReplaySessionORM,
)


@dataclass(frozen=True, slots=True)
class AdvanceResult:
    session: ReplaySessionORM
    duplicate: bool = False
    request_mismatch: bool = False
    version_conflict: bool = False


class ReplayRepository:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def create_session(
        self,
        *,
        user_id: str,
        instrument_id: str,
        provider: str,
        day: date,
        timeframe: str,
        mode: str,
        warmup_bars: int,
        context_days: int = 0,
    ) -> ReplaySessionORM:
        with self._factory() as session:
            orm = ReplaySessionORM(
                id=uuid.uuid4().hex,
                user_id=user_id,
                instrument_id=instrument_id,
                provider=provider,
                day=day,
                timeframe=timeframe,
                mode=mode,
                warmup_bars=warmup_bars,
                context_days=context_days,
                cursor_index=warmup_bars,
                cursor_version=0,
                state="running",
                sampling_mode="user_initiated",
            )
            session.add(orm)
            session.commit()
            session.refresh(orm)
            session.expunge(orm)
            return orm

    def get(self, session_id: str, user_id: str | None = None) -> ReplaySessionORM | None:
        with self._factory() as session:
            query = select(ReplaySessionORM).where(ReplaySessionORM.id == session_id)
            if user_id is not None:
                query = query.where(ReplaySessionORM.user_id == user_id)
            orm = session.scalar(query)
            if orm is not None:
                session.expunge(orm)
            return orm

    def list_sessions(self, user_id: str, limit: int = 100) -> list[ReplaySessionORM]:
        with self._factory() as session:
            rows = session.scalars(
                select(ReplaySessionORM)
                .where(ReplaySessionORM.user_id == user_id)
                .order_by(ReplaySessionORM.created_at.desc())
                .limit(limit)
            ).all()
            for row in rows:
                session.expunge(row)
            return list(rows)

    def update(self, orm: ReplaySessionORM, user_id: str, *, bump_cursor_version: bool = False) -> bool:
        with self._factory() as session:
            current = session.scalar(
                select(ReplaySessionORM).where(
                    ReplaySessionORM.id == orm.id,
                    ReplaySessionORM.user_id == user_id,
                )
            )
            if current is None:
                return False
            current.cursor_index = orm.cursor_index
            current.state = orm.state
            if bump_cursor_version:
                current.cursor_version += 1
                orm.cursor_version = current.cursor_version
            session.commit()
            return True

    def advance(
        self,
        *,
        session_id: str,
        user_id: str,
        n: int,
        last_index: int,
        expected_cursor_version: int | None,
        request_id: str | None,
    ) -> AdvanceResult | None:
        with self._factory() as session:
            orm = session.scalar(
                select(ReplaySessionORM).where(
                    ReplaySessionORM.id == session_id,
                    ReplaySessionORM.user_id == user_id,
                )
            )
            if orm is None:
                return None

            if request_id is not None:
                prior = session.scalar(
                    select(ReplayAdvanceRequestORM).where(
                        ReplayAdvanceRequestORM.session_id == session_id,
                        ReplayAdvanceRequestORM.request_id == request_id,
                    )
                )
                if prior is not None:
                    mismatch = (
                        prior.requested_n != n
                        or prior.expected_cursor_version != expected_cursor_version
                    )
                    orm.cursor_index = prior.result_cursor_index
                    orm.cursor_version = prior.result_cursor_version
                    session.expunge(orm)
                    return AdvanceResult(orm, duplicate=True, request_mismatch=mismatch)

            if expected_cursor_version is not None and orm.cursor_version != expected_cursor_version:
                session.expunge(orm)
                return AdvanceResult(orm, version_conflict=True)

            orm.cursor_index = min(orm.cursor_index + n, last_index)
            orm.cursor_version += 1
            if orm.cursor_index >= last_index:
                orm.state = "completed"
            if request_id is not None:
                session.add(
                    ReplayAdvanceRequestORM(
                        session_id=session_id,
                        request_id=request_id,
                        requested_n=n,
                        expected_cursor_version=expected_cursor_version,
                        result_cursor_index=orm.cursor_index,
                        result_cursor_version=orm.cursor_version,
                    )
                )
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                prior = session.scalar(
                    select(ReplayAdvanceRequestORM).where(
                        ReplayAdvanceRequestORM.session_id == session_id,
                        ReplayAdvanceRequestORM.request_id == request_id,
                    )
                )
                current = session.get(ReplaySessionORM, session_id)
                if prior is None or current is None:
                    raise
                current.cursor_index = prior.result_cursor_index
                current.cursor_version = prior.result_cursor_version
                session.expunge(current)
                return AdvanceResult(current, duplicate=True)
            session.refresh(orm)
            session.expunge(orm)
            return AdvanceResult(orm)

    def add_judgment(
        self,
        session_id: str,
        user_id: str,
        bar_index: int,
        bar_time_utc: datetime,
        payload: dict,
        client_request_id: str | None,
    ) -> tuple[JudgmentORM, bool]:
        with self._factory() as session:
            owned = session.scalar(
                select(ReplaySessionORM.id).where(
                    ReplaySessionORM.id == session_id,
                    ReplaySessionORM.user_id == user_id,
                )
            )
            if owned is None:
                raise LookupError(session_id)
            if client_request_id is not None:
                prior = session.scalar(
                    select(JudgmentORM).where(
                        JudgmentORM.session_id == session_id,
                        JudgmentORM.client_request_id == client_request_id,
                    )
                )
                if prior is not None:
                    session.expunge(prior)
                    return prior, True
            orm = JudgmentORM(
                session_id=session_id,
                bar_index=bar_index,
                bar_time_utc=bar_time_utc,
                client_request_id=client_request_id,
                payload=payload,
            )
            session.add(orm)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                prior = session.scalar(
                    select(JudgmentORM).where(
                        JudgmentORM.session_id == session_id,
                        JudgmentORM.client_request_id == client_request_id,
                    )
                )
                if prior is None:
                    raise
                session.expunge(prior)
                return prior, True
            session.refresh(orm)
            session.expunge(orm)
            return orm, False

    def list_judgments(self, session_id: str, user_id: str | None = None) -> list[JudgmentORM]:
        with self._factory() as session:
            query = (
                select(JudgmentORM)
                .join(ReplaySessionORM, ReplaySessionORM.id == JudgmentORM.session_id)
                .where(JudgmentORM.session_id == session_id)
                .order_by(JudgmentORM.id)
            )
            if user_id is not None:
                query = query.where(ReplaySessionORM.user_id == user_id)
            rows = session.scalars(query).all()
            for row in rows:
                session.expunge(row)
            return list(rows)

    def delete_judgment(self, session_id: str, judgment_id: int, user_id: str) -> bool:
        with self._factory() as session:
            orm = session.scalar(
                select(JudgmentORM)
                .join(ReplaySessionORM, ReplaySessionORM.id == JudgmentORM.session_id)
                .where(
                    JudgmentORM.id == judgment_id,
                    JudgmentORM.session_id == session_id,
                    ReplaySessionORM.user_id == user_id,
                )
            )
            if orm is None:
                return False
            session.delete(orm)
            session.commit()
            return True

    def delete_session(self, session_id: str, user_id: str) -> bool:
        with self._factory() as session:
            orm = session.scalar(
                select(ReplaySessionORM).where(
                    ReplaySessionORM.id == session_id,
                    ReplaySessionORM.user_id == user_id,
                )
            )
            if orm is None:
                return False
            session.delete(orm)
            session.commit()
            return True

    def add_annotation(
        self,
        session_id: str,
        user_id: str,
        bar_index: int,
        bar_time_utc: datetime,
        kind: str,
        label: str | None,
        text: str | None,
    ) -> AnnotationORM:
        with self._factory() as session:
            owned = session.scalar(
                select(ReplaySessionORM.id).where(
                    ReplaySessionORM.id == session_id,
                    ReplaySessionORM.user_id == user_id,
                )
            )
            if owned is None:
                raise LookupError(session_id)
            orm = AnnotationORM(
                session_id=session_id,
                bar_index=bar_index,
                bar_time_utc=bar_time_utc,
                kind=kind,
                label=label,
                text=text,
            )
            session.add(orm)
            session.commit()
            session.refresh(orm)
            session.expunge(orm)
            return orm

    def list_annotations(self, session_id: str, user_id: str) -> list[AnnotationORM]:
        with self._factory() as session:
            rows = session.scalars(
                select(AnnotationORM)
                .join(ReplaySessionORM, ReplaySessionORM.id == AnnotationORM.session_id)
                .where(AnnotationORM.session_id == session_id, ReplaySessionORM.user_id == user_id)
                .order_by(AnnotationORM.id)
            ).all()
            for row in rows:
                session.expunge(row)
            return list(rows)
