"""add fomc statement sentiment queue status fields

Revision ID: 20260609_0009
Revises: 20260609_0008
Create Date: 2026-06-09 23:25:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260609_0009"
down_revision = "20260609_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())
    if "fomc_event_details" not in table_names:
        return

    columns = {column["name"] for column in inspector.get_columns("fomc_event_details")}
    if "sentiment_status" not in columns:
        op.add_column("fomc_event_details", sa.Column("sentiment_status", sa.String(length=20), nullable=True))
    if "sentiment_queued_at" not in columns:
        op.add_column("fomc_event_details", sa.Column("sentiment_queued_at", sa.DateTime(), nullable=True))
    if "sentiment_extracted_at" not in columns:
        op.add_column("fomc_event_details", sa.Column("sentiment_extracted_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())
    if "fomc_event_details" not in table_names:
        return

    columns = {column["name"] for column in inspector.get_columns("fomc_event_details")}
    if "sentiment_extracted_at" in columns:
        op.drop_column("fomc_event_details", "sentiment_extracted_at")
    if "sentiment_queued_at" in columns:
        op.drop_column("fomc_event_details", "sentiment_queued_at")
    if "sentiment_status" in columns:
        op.drop_column("fomc_event_details", "sentiment_status")
