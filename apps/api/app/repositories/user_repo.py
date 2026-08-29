"""用户数据访问。"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models.orm import UserORM


class UserRepository:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def get(self, user_id: str) -> UserORM | None:
        with self._factory() as session:
            user = session.get(UserORM, user_id)
            if user is not None:
                session.expunge(user)
            return user

    def get_or_create(self, *, provider: str, subject: str, display_name: str | None = None) -> UserORM:
        with self._factory() as session:
            user = session.scalar(
                select(UserORM).where(UserORM.provider == provider, UserORM.subject == subject)
            )
            if user is None:
                user = UserORM(
                    id=uuid.uuid4().hex,
                    provider=provider,
                    subject=subject,
                    display_name=display_name,
                )
                session.add(user)
                session.commit()
                session.refresh(user)
            elif display_name and user.display_name != display_name:
                user.display_name = display_name
                session.commit()
            session.expunge(user)
            return user
