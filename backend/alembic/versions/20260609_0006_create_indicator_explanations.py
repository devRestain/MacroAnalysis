"""create indicator explanations table

Revision ID: 20260609_0006
Revises: 20260609_0005
Create Date: 2026-06-09 10:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260609_0006"
down_revision = "20260609_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if "indicator_explanations" not in inspector.get_table_names():
        op.create_table(
            "indicator_explanations",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("indicator_key", sa.String(length=100), nullable=False),
            sa.Column("display_name", sa.String(length=255), nullable=False),
            sa.Column("category", sa.String(length=64), nullable=True),
            sa.Column("provider", sa.String(length=128), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("short_label", sa.String(length=255), nullable=True),
            sa.Column("market_role", sa.Text(), nullable=True),
            sa.Column("higher_meaning", sa.Text(), nullable=True),
            sa.Column("lower_meaning", sa.Text(), nullable=True),
            sa.Column("watch_points", sa.JSON(), nullable=True),
            sa.Column("related_indicators", sa.JSON(), nullable=True),
            sa.Column("workflow_status", sa.JSON(), nullable=True),
            sa.Column("display_text", sa.JSON(), nullable=True),
            sa.Column("analysis_hints", sa.JSON(), nullable=True),
            sa.Column("source_schema_version", sa.String(length=32), nullable=False),
            sa.Column("source_file", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("indicator_key"),
        )

    index_names = {index["name"] for index in inspector.get_indexes("indicator_explanations")}
    if "ix_indicator_explanations_indicator_key" not in index_names:
        op.create_index(
            "ix_indicator_explanations_indicator_key",
            "indicator_explanations",
            ["indicator_key"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index("ix_indicator_explanations_indicator_key", table_name="indicator_explanations")
    op.drop_table("indicator_explanations")
