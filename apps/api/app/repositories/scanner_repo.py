"""Scanner 数据访问层（SQLite）。"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, sessionmaker

from app.models.orm import CandidateRecordORM, ScanTaskORM


class ScannerRepository:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def create_task(
        self,
        *,
        user_id: str,
        instrument_id: str,
        provider: str,
        timeframe: str,
        start_day: date,
        end_day: date,
        detector_ids: list[str],
        total_days: int,
    ) -> ScanTaskORM:
        with self._factory() as s:
            orm = ScanTaskORM(
                id=uuid.uuid4().hex,
                user_id=user_id,
                instrument_id=instrument_id,
                provider=provider,
                timeframe=timeframe,
                start_day=start_day,
                end_day=end_day,
                detector_ids=detector_ids,
                status="pending",
                total_days=total_days,
            )
            s.add(orm)
            s.commit()
            s.refresh(orm)
            return orm

    def get_task(self, task_id: str, user_id: str | None = None) -> ScanTaskORM | None:
        with self._factory() as s:
            query = select(ScanTaskORM).where(ScanTaskORM.id == task_id)
            if user_id is not None:
                query = query.where(ScanTaskORM.user_id == user_id)
            orm = s.scalar(query)
            if orm is not None:
                s.expunge(orm)
            return orm

    def list_tasks(self, user_id: str, limit: int = 50) -> list[ScanTaskORM]:
        with self._factory() as s:
            rows = s.scalars(
                select(ScanTaskORM)
                .where(ScanTaskORM.user_id == user_id)
                .order_by(desc(ScanTaskORM.created_at))
                .limit(limit)
            ).all()
            for r in rows:
                s.expunge(r)
            return list(rows)

    def update_task_progress(
        self,
        task_id: str,
        *,
        scanned_days: int,
        scanned_bars: int,
        candidate_count: int,
        progress: float,
        status: str = "running",
    ) -> None:
        with self._factory() as s:
            orm = s.get(ScanTaskORM, task_id)
            if orm:
                orm.scanned_days = scanned_days
                orm.scanned_bars = scanned_bars
                orm.candidate_count = candidate_count
                orm.progress = progress
                orm.status = status
                if orm.started_at is None:
                    orm.started_at = datetime.now(UTC)
                s.commit()

    def finish_task(self, task_id: str, *, status: str, error_message: str | None = None) -> None:
        with self._factory() as s:
            orm = s.get(ScanTaskORM, task_id)
            if orm:
                orm.status = status
                orm.finished_at = datetime.now(UTC)
                orm.progress = 1.0 if status == "completed" else orm.progress
                orm.error_message = error_message
                s.commit()

    def add_candidates(self, candidates: list[CandidateRecordORM]) -> None:
        if not candidates:
            return
        with self._factory() as s:
            s.add_all(candidates)
            s.commit()

    def get_candidate(self, candidate_id: str, user_id: str | None = None) -> CandidateRecordORM | None:
        with self._factory() as s:
            query = (
                select(CandidateRecordORM)
                .join(ScanTaskORM, ScanTaskORM.id == CandidateRecordORM.task_id)
                .where(CandidateRecordORM.id == candidate_id)
            )
            if user_id is not None:
                query = query.where(ScanTaskORM.user_id == user_id)
            orm = s.scalar(query)
            if orm is not None:
                s.expunge(orm)
            return orm

    def list_candidates(
        self,
        task_id: str | None = None,
        detector_id: str | None = None,
        review_status: str | None = None,
        only_favorites: bool = False,
        only_mistakes: bool = False,
        limit: int = 200,
        user_id: str | None = None,
    ) -> list[CandidateRecordORM]:
        with self._factory() as s:
            q = (
                select(CandidateRecordORM)
                .join(ScanTaskORM, ScanTaskORM.id == CandidateRecordORM.task_id)
            )
            if user_id is not None:
                q = q.where(ScanTaskORM.user_id == user_id)
            if task_id:
                q = q.where(CandidateRecordORM.task_id == task_id)
            if detector_id:
                q = q.where(CandidateRecordORM.detector_id == detector_id)
            if review_status:
                q = q.where(CandidateRecordORM.review_status == review_status)
            if only_favorites:
                q = q.where(CandidateRecordORM.is_favorite.is_(True))
            if only_mistakes:
                q = q.where(CandidateRecordORM.is_mistake_notebook.is_(True))
            q = q.order_by(desc(CandidateRecordORM.day), desc(CandidateRecordORM.bar_index)).limit(limit)
            rows = s.scalars(q).all()
            for r in rows:
                s.expunge(r)
            return list(rows)

    def review_candidate(
        self,
        candidate_id: str,
        *,
        user_id: str,
        review_status: str,
        rejection_reason: str | None,
        review_notes: str | None,
        is_favorite: bool | None,
        is_mistake_notebook: bool | None,
    ) -> CandidateRecordORM | None:
        with self._factory() as s:
            orm = s.scalar(
                select(CandidateRecordORM)
                .join(ScanTaskORM, ScanTaskORM.id == CandidateRecordORM.task_id)
                .where(
                    CandidateRecordORM.id == candidate_id,
                    ScanTaskORM.user_id == user_id,
                )
            )
            if not orm:
                return None
            orm.review_status = review_status
            if rejection_reason is not None:
                orm.rejection_reason = rejection_reason
            if review_notes is not None:
                orm.review_notes = review_notes
            if is_favorite is not None:
                orm.is_favorite = is_favorite
            if is_mistake_notebook is not None:
                orm.is_mistake_notebook = is_mistake_notebook
            orm.reviewed_at = datetime.now(UTC)
            s.commit()
            s.refresh(orm)
            s.expunge(orm)
            return orm
