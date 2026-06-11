"""create fed_watch table when missing

Revision ID: 20260611_0014
Revises: 20260611_0013
Create Date: 2026-06-11 20:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260611_0014"
down_revision = "20260611_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())

    if "fed_watch" not in table_names:
        op.create_table(
            "fed_watch",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("date", sa.DateTime(), nullable=False),
            sa.Column("meeting_date", sa.DateTime(), nullable=False),
            sa.Column("calendar_event_id", sa.Integer(), nullable=True),
            sa.Column("prob_hike", sa.Float(), nullable=True),
            sa.Column("prob_hold", sa.Float(), nullable=True),
            sa.Column("prob_cut", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["calendar_event_id"], ["economic_calendar_events.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("meeting_date", "date", name="uq_fed_watch_meeting_date_date"),
        )
        op.create_index("ix_fw_date_meeting", "fed_watch", ["date", "meeting_date"], unique=False)
        return

    columns = {column["name"] for column in inspector.get_columns("fed_watch")}
    if "calendar_event_id" not in columns:
        op.add_column("fed_watch", sa.Column("calendar_event_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_fed_watch_calendar_event_id",
            "fed_watch",
            "economic_calendar_events",
            ["calendar_event_id"],
            ["id"],
        )

    indexes = {index["name"] for index in inspector.get_indexes("fed_watch")}
    if "ix_fw_date_meeting" not in indexes:
        op.create_index("ix_fw_date_meeting", "fed_watch", ["date", "meeting_date"], unique=False)

    unique_constraints = {item["name"] for item in inspector.get_unique_constraints("fed_watch")}
    if "uq_fed_watch_meeting_date_date" not in unique_constraints:
        with op.batch_alter_table("fed_watch") as batch_op:
            batch_op.create_unique_constraint("uq_fed_watch_meeting_date_date", ["meeting_date", "date"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "fed_watch" not in inspector.get_table_names():
        return

    indexes = {index["name"] for index in inspector.get_indexes("fed_watch")}
    if "ix_fw_date_meeting" in indexes:
        op.drop_index("ix_fw_date_meeting", table_name="fed_watch")

    op.drop_table("fed_watch")
