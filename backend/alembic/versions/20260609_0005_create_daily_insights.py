"""create daily insights table

Revision ID: 20260609_0005
Revises: 20260609_0004
Create Date: 2026-06-09 00:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260609_0005"
down_revision = "20260609_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if "daily_insights" not in inspector.get_table_names():
        op.create_table(
            "daily_insights",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("as_of_date", sa.Date(), nullable=False),
            sa.Column("model", sa.String(length=100), nullable=True),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("key_points", sa.JSON(), nullable=True),
            sa.Column("risks", sa.JSON(), nullable=True),
            sa.Column("opportunities", sa.JSON(), nullable=True),
            sa.Column("source_observation_max_updated_at", sa.DateTime(), nullable=True),
            sa.Column("prompt_hash", sa.String(length=128), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("as_of_date"),
        )

    index_names = {index["name"] for index in inspector.get_indexes("daily_insights")}
    if "ix_daily_insights_status_updated_at" not in index_names:
        op.create_index(
            "ix_daily_insights_status_updated_at",
            "daily_insights",
            ["status", "updated_at"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index("ix_daily_insights_status_updated_at", table_name="daily_insights")
    op.drop_table("daily_insights")
