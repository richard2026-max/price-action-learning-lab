"""Scanner 业务服务层（MVP-D 核心）。

特点：
1. 确定性批处理：按交易日逐日加载 Parquet，前一日 RTH 预热 + 当日 RTH 5m 计算候选；
2. 封存考试集隔离：默认严格排除封存日，除非显式指定包含；
3. 严格无前视计算：复用同一套 `compute_candidates`（与回放端完全一致，保证可解释性与一致性）；
4. 任务状态追踪与人工审核闭环。
"""

from __future__ import annotations

import uuid
from datetime import date

from app.domain.bar import SessionType, Timeframe
from app.domain.instrument import Instrument
from app.models.orm import CandidateRecordORM, ScanTaskORM
from app.repositories.scanner_repo import ScannerRepository
from app.schemas.scanner import CreateScanTaskIn, ReviewCandidateIn
from app.services.calendar import XNYSCalendar
from app.services.detector_service import compute_candidates
from app.services.market_data import MarketDataStore
from app.services.sealed_exam import partition_days


class ScannerService:
    def __init__(self, store: MarketDataStore, calendar: XNYSCalendar, repo: ScannerRepository) -> None:
        self._store = store
        self._cal = calendar
        self._repo = repo

    def create_and_run_task(self, req: CreateScanTaskIn, instrument: Instrument, user_id: str) -> ScanTaskORM:
        start = date.fromisoformat(req.start_day)
        end = date.fromisoformat(req.end_day)
        all_trading_days = self._cal.trading_days(start, end)
        training_days, _ = partition_days(all_trading_days)
        target_days_iso = [d.isoformat() for d in all_trading_days] if req.include_sealed else training_days
        target_days = [date.fromisoformat(d) for d in target_days_iso]

        task = self._repo.create_task(
            user_id=user_id,
            instrument_id=instrument.instrument_id,
            provider=instrument.provider,
            timeframe=req.timeframe,
            start_day=start,
            end_day=end,
            detector_ids=req.detector_ids,
            total_days=len(target_days),
        )

        # 本地单用户：同步执行扫描任务
        try:
            self._execute_scan(task.id, instrument, target_days, set(req.detector_ids))
        except Exception as e:
            self._repo.finish_task(task.id, status="failed", error_message=str(e))
            raise

        return self._repo.get_task(task.id) or task

    def _execute_scan(
        self, task_id: str, instrument: Instrument, days: list[date], filter_detectors: set[str]
    ) -> None:
        total = len(days)
        scanned_bars = 0
        total_candidates = 0

        for idx, current_day in enumerate(days):
            rth = self._store.read_day(instrument, Timeframe.M5, current_day, SessionType.RTH)
            if not rth:
                continue

            prev_day = self._cal.prev_trading_day(current_day)
            prev_rth = self._store.read_day(instrument, Timeframe.M5, prev_day, SessionType.RTH)

            # 复用同一套候选计算逻辑（完全保证 no-lookahead 与可解释性）
            candidates = compute_candidates(prev_rth, rth)
            scanned_bars += len(rth)

            records: list[CandidateRecordORM] = []
            for c in candidates:
                if filter_detectors and c.detector_id not in filter_detectors:
                    continue
                records.append(CandidateRecordORM(
                    id=uuid.uuid4().hex,
                    task_id=task_id,
                    instrument_id=instrument.instrument_id,
                    provider=instrument.provider,
                    day=current_day,
                    bar_index=c.bar_index,
                    bar_time_utc=c.ts_event,
                    detector_id=c.detector_id,
                    detector_version=c.detector_version,
                    result_type=c.result_type,
                    result=c.result,
                    evidence=c.evidence,
                    rule_source=c.rule_source,
                    provenance=c.provenance,
                    review_status="unreviewed",
                ))

            if records:
                self._repo.add_candidates(records)
                total_candidates += len(records)

            progress = round((idx + 1) / total, 4) if total else 1.0
            self._repo.update_task_progress(
                task_id,
                scanned_days=idx + 1,
                scanned_bars=scanned_bars,
                candidate_count=total_candidates,
                progress=progress,
                status="running",
            )

        self._repo.finish_task(task_id, status="completed")

    def list_tasks(self, user_id: str) -> list[ScanTaskORM]:
        return self._repo.list_tasks(user_id)

    def get_task(self, task_id: str, user_id: str) -> ScanTaskORM | None:
        return self._repo.get_task(task_id, user_id)

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
        return self._repo.list_candidates(
            task_id=task_id,
            detector_id=detector_id,
            review_status=review_status,
            only_favorites=only_favorites,
            only_mistakes=only_mistakes,
            limit=limit,
            user_id=user_id,
        )

    def review_candidate(
        self, candidate_id: str, req: ReviewCandidateIn, user_id: str
    ) -> CandidateRecordORM | None:
        return self._repo.review_candidate(
            candidate_id,
            user_id=user_id,
            review_status=req.review_status.value,
            rejection_reason=req.rejection_reason.value if req.rejection_reason else None,
            review_notes=req.review_notes,
            is_favorite=req.is_favorite,
            is_mistake_notebook=req.is_mistake_notebook,
        )
