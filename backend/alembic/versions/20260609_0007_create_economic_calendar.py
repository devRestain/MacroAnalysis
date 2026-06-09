"""create economic calendar domain tables

Revision ID: 20260609_0007
Revises: 20260609_0006
Create Date: 2026-06-09 12:10:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260609_0007"
down_revision = "20260609_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if "economic_calendar_events" not in inspector.get_table_names():
        op.create_table(
            "economic_calendar_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("event_date", sa.DateTime(), nullable=False),
            sa.Column("event_end_date", sa.DateTime(), nullable=True),
            sa.Column("event_time", sa.String(length=20), nullable=True),
            sa.Column("timezone", sa.String(length=50), nullable=False, server_default="America/New_York"),
            sa.Column("event_key", sa.String(length=100), nullable=False),
            sa.Column("event_type", sa.String(length=50), nullable=False),
            sa.Column("category", sa.String(length=50), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("country", sa.String(length=20), nullable=False, server_default="US"),
            sa.Column("source", sa.String(length=100), nullable=False, server_default="unknown"),
            sa.Column("source_url", sa.Text(), nullable=True),
            sa.Column("importance", sa.String(length=20), nullable=False, server_default="medium"),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="scheduled"),
            sa.Column("related_indicator_key", sa.String(length=50), nullable=True),
            sa.Column("related_asset", sa.String(length=50), nullable=True),
            sa.Column("actual_value", sa.Float(), nullable=True),
            sa.Column("forecast_value", sa.Float(), nullable=True),
            sa.Column("previous_value", sa.Float(), nullable=True),
            sa.Column("unit", sa.String(length=30), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("event_key", "event_date", "source", name="uq_calendar_event_key_date_source"),
        )

    calendar_indexes = {index["name"] for index in inspector.get_indexes("economic_calendar_events")}
    if "ix_calendar_date_type" not in calendar_indexes:
        op.create_index("ix_calendar_date_type", "economic_calendar_events", ["event_date", "event_type"], unique=False)
    if "ix_calendar_key_date" not in calendar_indexes:
        op.create_index("ix_calendar_key_date", "economic_calendar_events", ["event_key", "event_date"], unique=False)

    if "fomc_event_details" not in inspector.get_table_names():
        op.create_table(
            "fomc_event_details",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("calendar_event_id", sa.Integer(), nullable=False),
            sa.Column("meeting_start_date", sa.DateTime(), nullable=True),
            sa.Column("meeting_end_date", sa.DateTime(), nullable=False),
            sa.Column("decision_rate", sa.Float(), nullable=True),
            sa.Column("target_rate_lower", sa.Float(), nullable=True),
            sa.Column("target_rate_upper", sa.Float(), nullable=True),
            sa.Column("change_bp", sa.Integer(), nullable=True),
            sa.Column("statement_url", sa.Text(), nullable=True),
            sa.Column("minutes_url", sa.Text(), nullable=True),
            sa.Column("implementation_note_url", sa.Text(), nullable=True),
            sa.Column("press_conference_url", sa.Text(), nullable=True),
            sa.Column("projection_materials_url", sa.Text(), nullable=True),
            sa.Column("has_sep", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["calendar_event_id"], ["economic_calendar_events.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("calendar_event_id"),
        )

    table_names = set(inspector.get_table_names())
    if "fed_watch" in table_names:
        fed_watch_columns = {column["name"] for column in inspector.get_columns("fed_watch")}
        if "calendar_event_id" not in fed_watch_columns:
            op.add_column("fed_watch", sa.Column("calendar_event_id", sa.Integer(), nullable=True))
            op.create_foreign_key(
                "fk_fed_watch_calendar_event_id",
                "fed_watch",
                "economic_calendar_events",
                ["calendar_event_id"],
                ["id"],
            )

    _backfill_fomc_calendar(bind, table_names=table_names)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())
    if "fed_watch" in table_names:
        fed_watch_columns = {column["name"] for column in inspector.get_columns("fed_watch")}
        if "calendar_event_id" in fed_watch_columns:
            op.drop_constraint("fk_fed_watch_calendar_event_id", "fed_watch", type_="foreignkey")
            op.drop_column("fed_watch", "calendar_event_id")

    op.drop_table("fomc_event_details")
    op.drop_index("ix_calendar_key_date", table_name="economic_calendar_events")
    op.drop_index("ix_calendar_date_type", table_name="economic_calendar_events")
    op.drop_table("economic_calendar_events")


def _backfill_fomc_calendar(bind, *, table_names: set[str]) -> None:
    if "fomc_events" not in table_names:
        return

    rows = bind.execute(
        sa.text(
            """
            SELECT id, meeting_date, decision_rate, change_bp, statement_url, minutes_url
            FROM fomc_events
            ORDER BY meeting_date
            """
        )
    ).mappings().all()

    for row in rows:
        event_id = bind.execute(
            sa.text(
                """
                INSERT INTO economic_calendar_events (
                    event_date, event_end_date, event_time, timezone, event_key, event_type,
                    category, title, country, source, source_url, importance, status, metadata_json
                ) VALUES (
                    :event_date, :event_end_date, :event_time, :timezone, :event_key, :event_type,
                    :category, :title, :country, :source, :source_url, :importance, :status, :metadata_json
                )
                ON CONFLICT (event_key, event_date, source) DO UPDATE SET
                    event_end_date = excluded.event_end_date,
                    event_time = excluded.event_time,
                    timezone = excluded.timezone,
                    category = excluded.category,
                    title = excluded.title,
                    country = excluded.country,
                    source_url = excluded.source_url,
                    importance = excluded.importance,
                    status = excluded.status,
                    metadata_json = excluded.metadata_json
                RETURNING id
                """
            ),
            {
                "event_date": row["meeting_date"],
                "event_end_date": row["meeting_date"],
                "event_time": "14:00",
                "timezone": "America/New_York",
                "event_key": "FOMC_MEETING",
                "event_type": "central_bank",
                "category": "fomc",
                "title": "FOMC Meeting",
                "country": "US",
                "source": "Federal Reserve",
                "source_url": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
                "importance": "high",
                "status": "released" if row["decision_rate"] is not None else "scheduled",
                "metadata_json": _json_value({"legacy_fomc_event_id": row["id"]}),
            },
        ).scalar_one()

        bind.execute(
            sa.text(
                """
                INSERT INTO fomc_event_details (
                    calendar_event_id, meeting_start_date, meeting_end_date, decision_rate, change_bp,
                    statement_url, minutes_url, has_sep
                ) VALUES (
                    :calendar_event_id, :meeting_start_date, :meeting_end_date, :decision_rate, :change_bp,
                    :statement_url, :minutes_url, :has_sep
                )
                ON CONFLICT (calendar_event_id) DO UPDATE SET
                    meeting_start_date = excluded.meeting_start_date,
                    meeting_end_date = excluded.meeting_end_date,
                    decision_rate = excluded.decision_rate,
                    change_bp = excluded.change_bp,
                    statement_url = excluded.statement_url,
                    minutes_url = excluded.minutes_url,
                    has_sep = excluded.has_sep
                """
            ),
            {
                "calendar_event_id": event_id,
                "meeting_start_date": row["meeting_date"],
                "meeting_end_date": row["meeting_date"],
                "decision_rate": row["decision_rate"],
                "change_bp": row["change_bp"],
                "statement_url": row["statement_url"],
                "minutes_url": row["minutes_url"],
                "has_sep": False,
            },
        )

        if "fed_watch" in table_names:
            bind.execute(
                sa.text(
                    """
                    UPDATE fed_watch
                    SET calendar_event_id = :calendar_event_id
                    WHERE meeting_date = :meeting_date AND calendar_event_id IS NULL
                    """
                ),
                {"calendar_event_id": event_id, "meeting_date": row["meeting_date"]},
            )


def _json_value(value: dict) -> str:
    import json

    return json.dumps(value)
