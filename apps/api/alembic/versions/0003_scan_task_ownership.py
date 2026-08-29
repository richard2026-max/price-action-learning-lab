"""scan task user ownership

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LEGACY_USER_ID = "00000000000000000000000000000001"


def upgrade() -> None:
    with op.batch_alter_table("scan_tasks") as batch:
        batch.add_column(sa.Column("user_id", sa.String(32), nullable=True))
    op.execute(
        sa.text("UPDATE scan_tasks SET user_id = :user_id WHERE user_id IS NULL").bindparams(
            user_id=LEGACY_USER_ID
        )
    )
    with op.batch_alter_table("scan_tasks") as batch:
        batch.alter_column("user_id", existing_type=sa.String(32), nullable=False)
        batch.create_foreign_key(
            "fk_scan_tasks_user_id_users", "users", ["user_id"], ["id"], ondelete="RESTRICT"
        )
        batch.create_index("ix_scan_tasks_user_id", ["user_id"])


def downgrade() -> None:
    with op.batch_alter_table("scan_tasks") as batch:
        batch.drop_index("ix_scan_tasks_user_id")
        batch.drop_constraint("fk_scan_tasks_user_id_users", type_="foreignkey")
        batch.drop_column("user_id")
