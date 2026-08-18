"""initial schema: replay_sessions / judgments / annotations / scan_tasks / candidate_records / sim_trades

Revision ID: 0001
Revises:
Create Date: 2026-08-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "replay_sessions",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("instrument_id", sa.String(16), nullable=False),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("timeframe", sa.String(4), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("sampling_mode", sa.String(24), nullable=False, server_default="user_initiated"),
        sa.Column("warmup_bars", sa.Integer(), nullable=False, server_default="6"),
        sa.Column("cursor_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("state", sa.String(16), nullable=False, server_default="running"),
        sa.Column("seed", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "judgments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_id", sa.String(32),
            sa.ForeignKey("replay_sessions.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("bar_index", sa.Integer(), nullable=False),
        sa.Column("bar_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "annotations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_id", sa.String(32),
            sa.ForeignKey("replay_sessions.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("bar_index", sa.Integer(), nullable=False),
        sa.Column("bar_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("label", sa.String(64), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "scan_tasks",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("instrument_id", sa.String(16), nullable=False),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("timeframe", sa.String(4), nullable=False, server_default="5m"),
        sa.Column("start_day", sa.Date(), nullable=False),
        sa.Column("end_day", sa.Date(), nullable=False),
        sa.Column("detector_ids", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("total_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scanned_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scanned_bars", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("candidate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "candidate_records",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column(
            "task_id", sa.String(32),
            sa.ForeignKey("scan_tasks.id", ondelete="CASCADE"), nullable=False, index=True,
        ),
        sa.Column("instrument_id", sa.String(16), nullable=False),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("day", sa.Date(), nullable=False, index=True),
        sa.Column("bar_index", sa.Integer(), nullable=False),
        sa.Column("bar_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detector_id", sa.String(32), nullable=False, index=True),
        sa.Column("detector_version", sa.String(16), nullable=False),
        sa.Column("result_type", sa.String(16), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("rule_source", sa.String(32), nullable=False),
        sa.Column("provenance", sa.String(32), nullable=False),
        sa.Column("review_status", sa.String(16), nullable=False, server_default="unreviewed"),
        sa.Column("rejection_reason", sa.String(64), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("is_mistake_notebook", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "sim_trades",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column(
            "session_id", sa.String(32),
            sa.ForeignKey("replay_sessions.id", ondelete="CASCADE"), nullable=False, index=True,
        ),
        sa.Column("instrument_id", sa.String(16), nullable=False),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("order_type", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("order_bar_index", sa.Integer(), nullable=False),
        sa.Column("order_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("planned_entry_price", sa.Float(), nullable=False),
        sa.Column("actual_entry_price", sa.Float(), nullable=True),
        sa.Column("entry_bar_index", sa.Integer(), nullable=True),
        sa.Column("entry_time_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stop_price", sa.Float(), nullable=False),
        sa.Column("target_price", sa.Float(), nullable=False),
        sa.Column("initial_risk", sa.Float(), nullable=False),
        sa.Column("exit_price", sa.Float(), nullable=True),
        sa.Column("exit_bar_index", sa.Integer(), nullable=True),
        sa.Column("exit_time_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exit_reason", sa.String(32), nullable=True),
        sa.Column("pnl", sa.Float(), nullable=True),
        sa.Column("pnl_in_r", sa.Float(), nullable=True),
        sa.Column("mfe_price", sa.Float(), nullable=True),
        sa.Column("mfe_in_r", sa.Float(), nullable=True),
        sa.Column("mae_price", sa.Float(), nullable=True),
        sa.Column("mae_in_r", sa.Float(), nullable=True),
        sa.Column("setup_notes", sa.Text(), nullable=True),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("sim_trades")
    op.drop_table("candidate_records")
    op.drop_table("scan_tasks")
    op.drop_table("annotations")
    op.drop_table("judgments")
    op.drop_table("replay_sessions")
