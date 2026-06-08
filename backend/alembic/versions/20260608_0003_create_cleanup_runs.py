"""create cleanup runs table

Revision ID: 20260608_0003
Revises: 20260608_0002
Create Date: 2026-06-08 01:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260608_0003"
down_revision = "20260608_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cleanup_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=False),
        sa.Column("collection_success_logs_deleted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("collection_failure_logs_deleted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("raw_responses_deleted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("debug_logs_deleted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scheduler_logs_deleted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cleanup_runs_started_at", "cleanup_runs", ["started_at"], unique=False)
    op.create_index("ix_cleanup_runs_created_at", "cleanup_runs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_cleanup_runs_created_at", table_name="cleanup_runs")
    op.drop_index("ix_cleanup_runs_started_at", table_name="cleanup_runs")
    op.drop_table("cleanup_runs")
