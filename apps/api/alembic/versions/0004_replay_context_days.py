"""replay sessions persist context_days

修复：get/advance/back 重建视图时按默认 context_days=0 加载，导致恢复会话或
推进K线后丢失前N日背景K线。将创建时的 context_days 持久化。

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("replay_sessions") as batch:
        batch.add_column(
            sa.Column("context_days", sa.Integer(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    with op.batch_alter_table("replay_sessions") as batch:
        batch.drop_column("context_days")
