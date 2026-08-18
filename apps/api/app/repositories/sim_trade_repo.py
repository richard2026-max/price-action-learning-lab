"""模拟交易仓储层（SQLite）。"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, sessionmaker

from app.models.orm import SimTradeORM


class SimTradeRepository:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def create_trade(self, orm: SimTradeORM) -> SimTradeORM:
        with self._factory() as s:
            s.add(orm)
            s.commit()
            s.refresh(orm)
            s.expunge(orm)
            return orm

    def get_trade(self, trade_id: str) -> SimTradeORM | None:
        with self._factory() as s:
            orm = s.get(SimTradeORM, trade_id)
            if orm:
                s.expunge(orm)
            return orm

    def update_trade(self, orm: SimTradeORM) -> None:
        with self._factory() as s:
            orm.updated_at = datetime.now(UTC)
            s.merge(orm)
            s.commit()

    def list_trades_for_session(self, session_id: str) -> list[SimTradeORM]:
        with self._factory() as s:
            rows = s.scalars(
                select(SimTradeORM)
                .where(SimTradeORM.session_id == session_id)
                .order_by(SimTradeORM.order_bar_index)
            ).all()
            for r in rows:
                s.expunge(r)
            return list(rows)

    def list_open_trades(self, session_id: str) -> list[SimTradeORM]:
        with self._factory() as s:
            rows = s.scalars(
                select(SimTradeORM)
                .where(
                    SimTradeORM.session_id == session_id,
                    SimTradeORM.status.in_(("pending", "open")),
                )
            ).all()
            for r in rows:
                s.expunge(r)
            return list(rows)

    def list_all_trades(self, limit: int = 100) -> list[SimTradeORM]:
        with self._factory() as s:
            rows = s.scalars(
                select(SimTradeORM).order_by(desc(SimTradeORM.created_at)).limit(limit)
            ).all()
            for r in rows:
                s.expunge(r)
            return list(rows)
