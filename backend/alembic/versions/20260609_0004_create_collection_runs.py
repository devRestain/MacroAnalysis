"""create collection runs table

Revision ID: 20260609_0004
Revises: 20260608_0003
Create Date: 2026-06-09 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260609_0004"
down_revision = "20260608_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "collection_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_key", sa.String(length=100), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("min_interval_minutes", sa.Integer(), nullable=False),
        sa.Column("fetched_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("inserted_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_collection_runs_job_key_started_at",
        "collection_runs",
        ["job_key", "started_at"],
        unique=False,
    )
    op.create_index(
        "ix_collection_runs_provider_target_date",
        "collection_runs",
        ["provider", "target_date"],
        unique=False,
    )
    op.create_index(
        "ix_collection_runs_status_finished_at",
        "collection_runs",
        ["status", "finished_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_collection_runs_status_finished_at", table_name="collection_runs")
    op.drop_index("ix_collection_runs_provider_target_date", table_name="collection_runs")
    op.drop_index("ix_collection_runs_job_key_started_at", table_name="collection_runs")
    op.drop_table("collection_runs")
