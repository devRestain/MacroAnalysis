"""deduplicate timeseries tables and add unique constraints

Revision ID: 20260608_0002
Revises: 20260608_0001
Create Date: 2026-06-08 00:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260608_0002"
down_revision = "20260608_0001"
branch_labels = None
depends_on = None


TIME_SERIES_TABLES = [
    (
        "interest_rates",
        ["series_key", "date"],
        "uq_interest_rates_series_key_date",
        False,
    ),
    (
        "macro_indicators",
        ["series_key", "date"],
        "uq_macro_indicators_series_key_date",
        False,
    ),
    (
        "credit_spreads",
        ["series_key", "date"],
        "uq_credit_spreads_series_key_date",
        False,
    ),
    (
        "equity_indices",
        ["ticker", "date"],
        "uq_equity_indices_ticker_date",
        False,
    ),
    (
        "sector_performance",
        ["ticker", "date"],
        "uq_sector_performance_ticker_date",
        False,
    ),
    (
        "real_economy",
        ["series_key", "date"],
        "uq_real_economy_series_key_date",
        False,
    ),
    (
        "exchange_rates",
        ["pair", "date"],
        "uq_exchange_rates_pair_date",
        True,
    ),
    (
        "fed_watch",
        ["meeting_date", "date"],
        "uq_fed_watch_meeting_date_date",
        True,
    ),
]


def _table_exists(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _unique_exists(inspector, table_name: str, constraint_name: str) -> bool:
    return any(
        constraint["name"] == constraint_name
        for constraint in inspector.get_unique_constraints(table_name)
    )


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _normalize_daily_timestamp(bind, table_name: str) -> None:
    if bind.dialect.name == "postgresql":
        op.execute(sa.text(f'UPDATE "{table_name}" SET date = date_trunc(\'day\', date) WHERE date IS NOT NULL'))
        return

    if bind.dialect.name == "sqlite":
        op.execute(
            sa.text(
                f"UPDATE {table_name} "
                "SET date = datetime(date, 'start of day') "
                "WHERE date IS NOT NULL"
            )
        )


def _deduplicate_table(inspector, bind, table_name: str, key_columns: list[str]) -> None:
    if not _table_exists(inspector, table_name):
        return

    order_parts = []
    is_postgres = bind.dialect.name == "postgresql"
    if _has_column(inspector, table_name, "updated_at"):
        order_parts.append("updated_at DESC NULLS LAST" if is_postgres else "updated_at IS NULL, updated_at DESC")
    if _has_column(inspector, table_name, "collected_at"):
        order_parts.append(
            "collected_at DESC NULLS LAST" if is_postgres else "collected_at IS NULL, collected_at DESC"
        )
    order_parts.append("id DESC")

    key_sql = ", ".join(key_columns)
    order_sql = ", ".join(order_parts)
    delete_sql = sa.text(
        f"""
        DELETE FROM "{table_name}"
        WHERE id IN (
            SELECT id
            FROM (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY {key_sql}
                        ORDER BY {order_sql}
                    ) AS row_num
                FROM "{table_name}"
            ) ranked
            WHERE ranked.row_num > 1
        )
        """
    )
    op.execute(delete_sql)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name, key_columns, constraint_name, normalize_date in TIME_SERIES_TABLES:
        if not _table_exists(inspector, table_name):
            continue
        if normalize_date:
            _normalize_daily_timestamp(bind, table_name)
        _deduplicate_table(inspector, bind, table_name, key_columns)
        if _unique_exists(inspector, table_name, constraint_name):
            continue
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.create_unique_constraint(constraint_name, key_columns)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name, _, constraint_name, _ in TIME_SERIES_TABLES:
        if not _table_exists(inspector, table_name):
            continue
        if not _unique_exists(inspector, table_name, constraint_name):
            continue
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_constraint(constraint_name, type_="unique")
