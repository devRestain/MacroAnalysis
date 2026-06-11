"""expand economic calendar event metadata

Revision ID: 20260611_0013
Revises: 20260611_0012
Create Date: 2026-06-11 19:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260611_0013"
down_revision = "20260611_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if "economic_calendar_events" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("economic_calendar_events")}

    _add_column_if_missing("economic_calendar_events", columns, "event_datetime_utc", sa.Column("event_datetime_utc", sa.DateTime(), nullable=True))
    _add_column_if_missing("economic_calendar_events", columns, "event_date_local", sa.Column("event_date_local", sa.Date(), nullable=True))
    _add_column_if_missing("economic_calendar_events", columns, "event_time_local", sa.Column("event_time_local", sa.String(length=20), nullable=True))
    _add_column_if_missing("economic_calendar_events", columns, "display_name", sa.Column("display_name", sa.String(length=200), nullable=True))
    _add_column_if_missing("economic_calendar_events", columns, "short_name", sa.Column("short_name", sa.String(length=100), nullable=True))
    _add_column_if_missing("economic_calendar_events", columns, "date_precision", sa.Column("date_precision", sa.String(length=32), nullable=True))
    _add_column_if_missing("economic_calendar_events", columns, "time_source", sa.Column("time_source", sa.String(length=32), nullable=True))
    _add_column_if_missing("economic_calendar_events", columns, "time_confidence", sa.Column("time_confidence", sa.String(length=32), nullable=True))
    _add_column_if_missing("economic_calendar_events", columns, "related_indicator_keys", sa.Column("related_indicator_keys", sa.JSON(), nullable=True))
    _add_column_if_missing("economic_calendar_events", columns, "beginner_description", sa.Column("beginner_description", sa.Text(), nullable=True))
    _add_column_if_missing("economic_calendar_events", columns, "why_it_matters", sa.Column("why_it_matters", sa.Text(), nullable=True))
    _add_column_if_missing("economic_calendar_events", columns, "watch_items", sa.Column("watch_items", sa.JSON(), nullable=True))

    bind.execute(
        sa.text(
            """
            UPDATE economic_calendar_events
            SET
                event_datetime_utc = COALESCE(event_datetime_utc, event_date),
                event_date_local = COALESCE(event_date_local, CAST(event_date AS DATE)),
                event_time_local = COALESCE(event_time_local, event_time),
                display_name = COALESCE(display_name, title),
                short_name = COALESCE(short_name, title),
                date_precision = COALESCE(
                    date_precision,
                    CASE WHEN COALESCE(event_time_local, event_time) IS NULL THEN 'date_only' ELSE 'datetime_estimated' END
                ),
                time_source = COALESCE(
                    time_source,
                    CASE WHEN COALESCE(event_time_local, event_time) IS NULL THEN NULL ELSE 'legacy' END
                ),
                time_confidence = COALESCE(
                    time_confidence,
                    CASE WHEN COALESCE(event_time_local, event_time) IS NULL THEN NULL ELSE 'estimated' END
                ),
                related_indicator_keys = COALESCE(
                    related_indicator_keys,
                    CASE
                        WHEN related_indicator_key IS NULL THEN NULL
                        ELSE json_build_array(related_indicator_key)
                    END
                )
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "economic_calendar_events" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("economic_calendar_events")}
    for column_name in (
        "watch_items",
        "why_it_matters",
        "beginner_description",
        "related_indicator_keys",
        "time_confidence",
        "time_source",
        "date_precision",
        "short_name",
        "display_name",
        "event_time_local",
        "event_date_local",
        "event_datetime_utc",
    ):
        if column_name in columns:
            op.drop_column("economic_calendar_events", column_name)


def _add_column_if_missing(
    table_name: str,
    columns: set[str],
    column_name: str,
    column: sa.Column,
) -> None:
    if column_name in columns:
        return
    op.add_column(table_name, column)
