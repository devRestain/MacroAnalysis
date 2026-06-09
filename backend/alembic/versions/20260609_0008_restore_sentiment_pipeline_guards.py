"""restore sentiment pipeline tables and idempotency guards

Revision ID: 20260609_0008
Revises: 20260609_0007
Create Date: 2026-06-09 22:40:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260609_0008"
down_revision = "20260609_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())

    if "news_items" in table_names:
        news_columns = {column["name"] for column in inspector.get_columns("news_items")}
        if "sentiment_extracted" not in news_columns:
            op.add_column(
                "news_items",
                sa.Column("sentiment_extracted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            )

    if "sentiment_signals" not in table_names:
        op.create_table(
            "sentiment_signals",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("source_type", sa.String(length=20), nullable=False),
            sa.Column("source_id", sa.Integer(), nullable=False),
            sa.Column("extracted_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
            sa.Column("batch_date", sa.DateTime(), nullable=False),
            sa.Column("actor", sa.String(length=30), nullable=False),
            sa.Column("dimension", sa.String(length=30), nullable=False),
            sa.Column("stance", sa.String(length=30), nullable=False),
            sa.Column("stance_score", sa.Float(), nullable=False),
            sa.Column("intensity", sa.Float(), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("evidence", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "source_type",
                "source_id",
                "batch_date",
                "actor",
                "dimension",
                "stance",
                name="uq_sentiment_signal_source_batch_actor_dimension_stance",
            ),
        )

    if "expectations" not in table_names:
        op.create_table(
            "expectations",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("date", sa.DateTime(), nullable=False),
            sa.Column("actor", sa.String(length=30), nullable=False),
            sa.Column("dimension", sa.String(length=30), nullable=False),
            sa.Column("consensus_score", sa.Float(), nullable=False),
            sa.Column("raw_score", sa.Float(), nullable=False),
            sa.Column("consensus_strength", sa.Float(), nullable=False),
            sa.Column("inertia_age_days", sa.Float(), nullable=True),
            sa.Column("inertia_coefficient", sa.Float(), nullable=True),
            sa.Column("inertia_reset", sa.Boolean(), nullable=True),
            sa.Column("consensus_7d_ago", sa.Float(), nullable=True),
            sa.Column("momentum_score", sa.Float(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("date", "actor", "dimension", name="uq_expectation_date_actor_dimension"),
        )

    if "divergence_events" not in table_names:
        op.create_table(
            "divergence_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("detected_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
            sa.Column("batch_date", sa.DateTime(), nullable=False),
            sa.Column("actor", sa.String(length=30), nullable=False),
            sa.Column("dimension", sa.String(length=30), nullable=False),
            sa.Column("raw_score", sa.Float(), nullable=False),
            sa.Column("consensus_score", sa.Float(), nullable=False),
            sa.Column("consensus_strength", sa.Float(), nullable=False),
            sa.Column("adjusted_gap", sa.Float(), nullable=False),
            sa.Column("severity", sa.String(length=10), nullable=False),
            sa.Column("inertia_coefficient", sa.Float(), nullable=True),
            sa.Column("inertia_reset", sa.Boolean(), nullable=True),
            sa.Column("momentum_score", sa.Float(), nullable=True),
            sa.Column("momentum_sign_change", sa.Boolean(), nullable=True),
            sa.Column("multiplier_applied", sa.Float(), nullable=True),
            sa.Column("report_generated", sa.Boolean(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "batch_date",
                "actor",
                "dimension",
                name="uq_divergence_event_batch_actor_dimension",
            ),
        )

    if "divergence_reports" not in table_names:
        op.create_table(
            "divergence_reports",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("event_id", sa.Integer(), nullable=False),
            sa.Column("generated_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
            sa.Column("headline", sa.Text(), nullable=False),
            sa.Column("background", sa.Text(), nullable=True),
            sa.Column("evidence", sa.Text(), nullable=True),
            sa.Column("action_plan", sa.Text(), nullable=True),
            sa.Column("risk_scenario", sa.Text(), nullable=True),
            sa.Column("notified", sa.Boolean(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("event_id", name="uq_divergence_report_event_id"),
        )

    _ensure_indexes_and_constraints()


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())

    if "divergence_reports" in table_names:
        unique_names = {item["name"] for item in inspector.get_unique_constraints("divergence_reports")}
        if "uq_divergence_report_event_id" in unique_names:
            op.drop_constraint("uq_divergence_report_event_id", "divergence_reports", type_="unique")

    if "divergence_events" in table_names:
        unique_names = {item["name"] for item in inspector.get_unique_constraints("divergence_events")}
        if "uq_divergence_event_batch_actor_dimension" in unique_names:
            op.drop_constraint("uq_divergence_event_batch_actor_dimension", "divergence_events", type_="unique")

    if "expectations" in table_names:
        unique_names = {item["name"] for item in inspector.get_unique_constraints("expectations")}
        if "uq_expectation_date_actor_dimension" in unique_names:
            op.drop_constraint("uq_expectation_date_actor_dimension", "expectations", type_="unique")

    if "sentiment_signals" in table_names:
        unique_names = {item["name"] for item in inspector.get_unique_constraints("sentiment_signals")}
        if "uq_sentiment_signal_source_batch_actor_dimension_stance" in unique_names:
            op.drop_constraint(
                "uq_sentiment_signal_source_batch_actor_dimension_stance",
                "sentiment_signals",
                type_="unique",
            )


def _ensure_indexes_and_constraints() -> None:
    inspector = inspect(op.get_bind())
    _ensure_constraint(
        inspector,
        table_name="sentiment_signals",
        constraint_name="uq_sentiment_signal_source_batch_actor_dimension_stance",
        columns=["source_type", "source_id", "batch_date", "actor", "dimension", "stance"],
    )
    _ensure_constraint(
        inspector,
        table_name="expectations",
        constraint_name="uq_expectation_date_actor_dimension",
        columns=["date", "actor", "dimension"],
    )
    _ensure_constraint(
        inspector,
        table_name="divergence_events",
        constraint_name="uq_divergence_event_batch_actor_dimension",
        columns=["batch_date", "actor", "dimension"],
    )
    _ensure_constraint(
        inspector,
        table_name="divergence_reports",
        constraint_name="uq_divergence_report_event_id",
        columns=["event_id"],
    )
    _ensure_index(inspector, "sentiment_signals", "ix_ss_batch_actor_dim", ["batch_date", "actor", "dimension"])
    _ensure_index(inspector, "sentiment_signals", "ix_ss_source", ["source_type", "source_id"])
    _ensure_index(inspector, "expectations", "ix_exp_date_actor_dim", ["date", "actor", "dimension"])
    _ensure_index(inspector, "divergence_events", "ix_de_batch_severity", ["batch_date", "severity"])
    _ensure_index(inspector, "divergence_events", "ix_de_actor_dim", ["actor", "dimension"])
    _ensure_index(inspector, "divergence_reports", "ix_dr_event_id", ["event_id"])


def _ensure_constraint(inspector, *, table_name: str, constraint_name: str, columns: list[str]) -> None:
    unique_names = {item["name"] for item in inspector.get_unique_constraints(table_name)}
    if constraint_name not in unique_names:
        op.create_unique_constraint(constraint_name, table_name, columns)


def _ensure_index(inspector, table_name: str, index_name: str, columns: list[str]) -> None:
    index_names = {index["name"] for index in inspector.get_indexes(table_name)}
    if index_name not in index_names:
        op.create_index(index_name, table_name, columns, unique=False)
