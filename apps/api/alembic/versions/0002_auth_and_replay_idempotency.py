"""add users, replay ownership and idempotency

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-29
"""

from datetime import UTC, datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LEGACY_USER_ID = "00000000000000000000000000000001"


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("subject", sa.String(128), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider", "subject", name="uq_users_provider_subject"),
    )
    users = sa.table(
        "users",
        sa.column("id", sa.String),
        sa.column("provider", sa.String),
        sa.column("subject", sa.String),
        sa.column("display_name", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    now = datetime.now(UTC)
    op.bulk_insert(
        users,
        [
            {
                "id": LEGACY_USER_ID,
                "provider": "local",
                "subject": "legacy",
                "display_name": "Legacy Local User",
                "created_at": now,
                "updated_at": now,
            }
        ],
    )

    with op.batch_alter_table("replay_sessions") as batch:
        batch.add_column(sa.Column("user_id", sa.String(32), nullable=True))
        batch.add_column(
            sa.Column("cursor_version", sa.Integer(), nullable=False, server_default="0")
        )
    op.execute(
        sa.text("UPDATE replay_sessions SET user_id = :user_id WHERE user_id IS NULL").bindparams(
            user_id=LEGACY_USER_ID
        )
    )
    with op.batch_alter_table("replay_sessions") as batch:
        batch.alter_column("user_id", existing_type=sa.String(32), nullable=False)
        batch.create_foreign_key(
            "fk_replay_sessions_user_id_users", "users", ["user_id"], ["id"], ondelete="RESTRICT"
        )
        batch.create_index("ix_replay_sessions_user_id", ["user_id"])

    with op.batch_alter_table("judgments") as batch:
        batch.add_column(sa.Column("client_request_id", sa.String(128), nullable=True))
        batch.create_unique_constraint(
            "uq_judgment_request", ["session_id", "client_request_id"]
        )

    op.create_table(
        "replay_advance_requests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.String(32),
            sa.ForeignKey("replay_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("request_id", sa.String(128), nullable=False),
        sa.Column("requested_n", sa.Integer(), nullable=False),
        sa.Column("expected_cursor_version", sa.Integer(), nullable=True),
        sa.Column("result_cursor_index", sa.Integer(), nullable=False),
        sa.Column("result_cursor_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id", "request_id", name="uq_replay_advance_request"),
    )
    op.create_index(
        "ix_replay_advance_requests_session_id", "replay_advance_requests", ["session_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_replay_advance_requests_session_id", table_name="replay_advance_requests")
    op.drop_table("replay_advance_requests")
    with op.batch_alter_table("judgments") as batch:
        batch.drop_constraint("uq_judgment_request", type_="unique")
        batch.drop_column("client_request_id")
    with op.batch_alter_table("replay_sessions") as batch:
        batch.drop_index("ix_replay_sessions_user_id")
        batch.drop_constraint("fk_replay_sessions_user_id_users", type_="foreignkey")
        batch.drop_column("cursor_version")
        batch.drop_column("user_id")
    op.drop_table("users")
