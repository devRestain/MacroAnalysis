"""generalize communication events and ai summaries

Revision ID: 20260611_0012
Revises: 20260610_0011
Create Date: 2026-06-11 10:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260611_0012"
down_revision = "20260610_0011"
branch_labels = None
depends_on = None


communication_events = sa.table(
    "communication_events",
    sa.column("id", sa.Integer()),
    sa.column("event_date", sa.DateTime()),
    sa.column("source", sa.String(length=100)),
    sa.column("title", sa.String(length=255)),
    sa.column("event_type", sa.String(length=50)),
    sa.column("url", sa.Text()),
    sa.column("institution", sa.String(length=100)),
    sa.column("country", sa.String(length=20)),
    sa.column("content_text", sa.Text()),
    sa.column("meeting_date", sa.DateTime()),
    sa.column("decision_rate", sa.Float()),
    sa.column("change_bp", sa.Integer()),
    sa.column("statement_url", sa.Text()),
    sa.column("minutes_url", sa.Text()),
    sa.column("projection_url", sa.Text()),
    sa.column("metadata_json", sa.JSON()),
    sa.column("sentiment_status", sa.String(length=20)),
    sa.column("sentiment_queued_at", sa.DateTime()),
    sa.column("sentiment_extracted_at", sa.DateTime()),
)

legacy_fomc_events = sa.table(
    "fomc_events",
    sa.column("id", sa.Integer()),
    sa.column("meeting_date", sa.DateTime()),
    sa.column("decision_rate", sa.Float()),
    sa.column("change_bp", sa.Integer()),
    sa.column("statement_url", sa.Text()),
    sa.column("minutes_url", sa.Text()),
)

ai_summaries = sa.table(
    "ai_summaries",
    sa.column("id", sa.Integer()),
    sa.column("summary_date", sa.DateTime()),
    sa.column("summary_type", sa.String(length=50)),
    sa.column("target_key", sa.String(length=128)),
    sa.column("headline", sa.Text()),
    sa.column("body", sa.Text()),
    sa.column("indicators_snapshot", sa.JSON()),
    sa.column("model_used", sa.String(length=50)),
    sa.column("metadata_json", sa.JSON()),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "communication_events" not in table_names:
        op.create_table(
            "communication_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("event_date", sa.DateTime(), nullable=False),
            sa.Column("source", sa.String(length=100), nullable=False, server_default="Federal Reserve"),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("event_type", sa.String(length=50), nullable=False),
            sa.Column("url", sa.Text(), nullable=True),
            sa.Column("institution", sa.String(length=100), nullable=False, server_default="Federal Reserve"),
            sa.Column("country", sa.String(length=20), nullable=False, server_default="US"),
            sa.Column("content_text", sa.Text(), nullable=True),
            sa.Column("meeting_date", sa.DateTime(), nullable=True),
            sa.Column("decision_rate", sa.Float(), nullable=True),
            sa.Column("change_bp", sa.Integer(), nullable=True),
            sa.Column("statement_url", sa.Text(), nullable=True),
            sa.Column("minutes_url", sa.Text(), nullable=True),
            sa.Column("projection_url", sa.Text(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("sentiment_status", sa.String(length=20), nullable=True),
            sa.Column("sentiment_queued_at", sa.DateTime(), nullable=True),
            sa.Column("sentiment_extracted_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("source", "event_type", "event_date", "title", name="uq_communication_event_identity"),
        )
        op.create_index("ix_communication_events_type_date", "communication_events", ["event_type", "event_date"], unique=False)
        op.create_index("ix_communication_events_source_date", "communication_events", ["source", "event_date"], unique=False)

    if "fomc_events" in table_names:
        rows = bind.execute(
            sa.select(
                legacy_fomc_events.c.meeting_date,
                legacy_fomc_events.c.decision_rate,
                legacy_fomc_events.c.change_bp,
                legacy_fomc_events.c.statement_url,
                legacy_fomc_events.c.minutes_url,
            )
        ).fetchall()
        for row in rows:
            exists = bind.execute(
                sa.select(communication_events.c.id).where(
                    communication_events.c.source == "Federal Reserve",
                    communication_events.c.event_type == "fomc_meeting",
                    communication_events.c.event_date == row.meeting_date,
                    communication_events.c.title == "FOMC Meeting",
                )
            ).first()
            if exists:
                continue
            bind.execute(
                communication_events.insert().values(
                    event_date=row.meeting_date,
                    source="Federal Reserve",
                    title="FOMC Meeting",
                    event_type="fomc_meeting",
                    url=row.statement_url or row.minutes_url,
                    institution="Federal Reserve",
                    country="US",
                    content_text=None,
                    meeting_date=row.meeting_date,
                    decision_rate=row.decision_rate,
                    change_bp=row.change_bp,
                    statement_url=row.statement_url,
                    minutes_url=row.minutes_url,
                    projection_url=None,
                    metadata_json={},
                    sentiment_status=None,
                    sentiment_queued_at=None,
                    sentiment_extracted_at=None,
                )
            )
        op.drop_table("fomc_events")

    if "ai_summaries" not in table_names:
        op.create_table(
            "ai_summaries",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("summary_date", sa.DateTime(), nullable=False),
            sa.Column("summary_type", sa.String(length=50), nullable=False, server_default="macro"),
            sa.Column("target_key", sa.String(length=128), nullable=True),
            sa.Column("headline", sa.Text(), nullable=True),
            sa.Column("body", sa.Text(), nullable=True),
            sa.Column("indicators_snapshot", sa.JSON(), nullable=True),
            sa.Column("model_used", sa.String(length=50), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("summary_date", "summary_type", "target_key", name="uq_ai_summary_scope"),
        )
    else:
        columns = {column["name"] for column in inspector.get_columns("ai_summaries")}
        with op.batch_alter_table("ai_summaries") as batch_op:
            if "summary_type" not in columns:
                batch_op.add_column(sa.Column("summary_type", sa.String(length=50), nullable=True, server_default="macro"))
            if "target_key" not in columns:
                batch_op.add_column(sa.Column("target_key", sa.String(length=128), nullable=True))
            if "metadata_json" not in columns:
                batch_op.add_column(sa.Column("metadata_json", sa.JSON(), nullable=True))

        bind.execute(ai_summaries.update().where(ai_summaries.c.summary_type.is_(None)).values(summary_type="macro"))
        with op.batch_alter_table("ai_summaries") as batch_op:
            batch_op.alter_column("summary_type", existing_type=sa.String(length=50), nullable=False, server_default="macro")

        inspector = sa.inspect(bind)
        unique_names = {item["name"] for item in inspector.get_unique_constraints("ai_summaries") if item.get("name")}
        with op.batch_alter_table("ai_summaries") as batch_op:
            for unique_name in unique_names:
                if unique_name != "uq_ai_summary_scope":
                    batch_op.drop_constraint(unique_name, type_="unique")
            if "uq_ai_summary_scope" not in unique_names:
                batch_op.create_unique_constraint("uq_ai_summary_scope", ["summary_date", "summary_type", "target_key"])

    inspector = sa.inspect(bind)
    index_names = {item["name"] for item in inspector.get_indexes("ai_summaries") if item.get("name")}
    if "ix_ai_summaries_type_date" not in index_names:
        op.create_index("ix_ai_summaries_type_date", "ai_summaries", ["summary_type", "summary_date"], unique=False)
    if "ix_ai_summaries_target_date" not in index_names:
        op.create_index("ix_ai_summaries_target_date", "ai_summaries", ["target_key", "summary_date"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "fomc_events" not in table_names:
        op.create_table(
            "fomc_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("meeting_date", sa.DateTime(), nullable=False),
            sa.Column("decision_rate", sa.Float(), nullable=True),
            sa.Column("change_bp", sa.Integer(), nullable=True),
            sa.Column("statement_url", sa.Text(), nullable=True),
            sa.Column("minutes_url", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("meeting_date"),
        )
        if "communication_events" in table_names:
            rows = bind.execute(
                sa.select(
                    communication_events.c.meeting_date,
                    communication_events.c.decision_rate,
                    communication_events.c.change_bp,
                    communication_events.c.statement_url,
                    communication_events.c.minutes_url,
                ).where(communication_events.c.event_type == "fomc_meeting")
            ).fetchall()
            for row in rows:
                bind.execute(
                    legacy_fomc_events.insert().values(
                        meeting_date=row.meeting_date,
                        decision_rate=row.decision_rate,
                        change_bp=row.change_bp,
                        statement_url=row.statement_url,
                        minutes_url=row.minutes_url,
                    )
                )
            op.drop_index("ix_communication_events_type_date", table_name="communication_events")
            op.drop_index("ix_communication_events_source_date", table_name="communication_events")
            op.drop_table("communication_events")

    if "ai_summaries" in table_names:
        with op.batch_alter_table("ai_summaries") as batch_op:
            index_names = {item["name"] for item in inspector.get_indexes("ai_summaries") if item.get("name")}
            unique_names = {item["name"] for item in inspector.get_unique_constraints("ai_summaries") if item.get("name")}
            if "ix_ai_summaries_type_date" in index_names:
                batch_op.drop_index("ix_ai_summaries_type_date")
            if "ix_ai_summaries_target_date" in index_names:
                batch_op.drop_index("ix_ai_summaries_target_date")
            if "uq_ai_summary_scope" in unique_names:
                batch_op.drop_constraint("uq_ai_summary_scope", type_="unique")
            columns = {column["name"] for column in inspector.get_columns("ai_summaries")}
            if "metadata_json" in columns:
                batch_op.drop_column("metadata_json")
            if "target_key" in columns:
                batch_op.drop_column("target_key")
            if "summary_type" in columns:
                batch_op.drop_column("summary_type")
            batch_op.create_unique_constraint("uq_ai_summaries_summary_date", ["summary_date"])
