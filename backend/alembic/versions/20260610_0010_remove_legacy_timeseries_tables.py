"""remove legacy time-series tables and tighten observation uniqueness

Revision ID: 20260610_0010
Revises: 20260609_0009
Create Date: 2026-06-10 20:30:00
"""

from __future__ import annotations

from datetime import date, datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert


revision = "20260610_0010"
down_revision = "20260609_0009"
branch_labels = None
depends_on = None


LEGACY_TABLES = [
    "interest_rates",
    "macro_indicators",
    "exchange_rates",
    "equity_indices",
    "sector_performance",
    "credit_spreads",
    "real_economy",
    "sentiment_indicators",
]

LEGACY_BACKFILL_TABLES = [
    ("interest_rates", "series_key", "value", "date", "rates", "fred"),
    ("macro_indicators", "series_key", "value", "date", "macro", "fred"),
    ("credit_spreads", "series_key", "value", "date", "credit", "fred"),
    ("equity_indices", "ticker", "close", "date", "equity", "yfinance"),
    ("exchange_rates", "pair", "value", "date", "fx", "exchangerate-api"),
    ("real_economy", "series_key", "value", "date", "real", "yfinance"),
    ("sector_performance", "ticker", "close", "date", "sector", "yfinance"),
]

INDICATOR_DEFAULTS = {
    "DFF": {"name": "Fed Funds Rate", "country": "US", "frequency": "daily", "unit": "%"},
    "DGS2": {"name": "2Y Treasury Yield", "country": "US", "frequency": "daily", "unit": "%"},
    "DGS10": {"name": "10Y Treasury Yield", "country": "US", "frequency": "daily", "unit": "%"},
    "DGS30": {"name": "30Y Treasury Yield", "country": "US", "frequency": "daily", "unit": "%"},
    "T10Y2Y": {"name": "10Y-2Y Spread", "country": "US", "frequency": "daily", "unit": "%"},
    "SOFR": {"name": "SOFR", "country": "US", "frequency": "daily", "unit": "%"},
    "CPIAUCSL": {"name": "CPI", "country": "US", "frequency": "monthly", "unit": "index"},
    "PCEPILFE": {"name": "Core PCE", "country": "US", "frequency": "monthly", "unit": "index"},
    "GDPC1": {"name": "Real GDP", "country": "US", "frequency": "quarterly", "unit": "index"},
    "UNRATE": {"name": "Unemployment Rate", "country": "US", "frequency": "monthly", "unit": "%"},
    "ICSA": {"name": "Initial Jobless Claims", "country": "US", "frequency": "weekly", "unit": "count"},
    "M2SL": {"name": "M2 Money Supply", "country": "US", "frequency": "monthly", "unit": "billions"},
    "USSLIND": {"name": "Leading Economic Index", "country": "US", "frequency": "monthly", "unit": "index"},
    "MANEMP": {"name": "Manufacturing Employment", "country": "US", "frequency": "monthly", "unit": "thousands"},
    "HY_OAS": {"name": "HY OAS", "country": "US", "frequency": "daily", "unit": "bp"},
    "IG_OAS": {"name": "IG OAS", "country": "US", "frequency": "daily", "unit": "bp"},
    "^GSPC": {"name": "S&P 500", "country": "US", "frequency": "daily", "unit": "index"},
    "^IXIC": {"name": "NASDAQ", "country": "US", "frequency": "daily", "unit": "index"},
    "^KS11": {"name": "KOSPI", "country": "KR", "frequency": "daily", "unit": "index"},
    "^N225": {"name": "Nikkei 225", "country": "JP", "frequency": "daily", "unit": "index"},
    "^GDAXI": {"name": "DAX", "country": "DE", "frequency": "daily", "unit": "index"},
    "^SSEC": {"name": "Shanghai Composite", "country": "CN", "frequency": "daily", "unit": "index"},
    "000001.SS": {"name": "Shanghai Composite", "country": "CN", "frequency": "daily", "unit": "index"},
    "^VIX": {"name": "VIX", "country": "US", "frequency": "daily", "unit": "index"},
    "^TNX": {"name": "10Y Treasury Yield (Market)", "country": "US", "frequency": "daily", "unit": "%"},
    "DX-Y.NYB": {"name": "DXY", "country": "US", "frequency": "daily", "unit": "index"},
    "CL=F": {"name": "WTI Crude", "country": "US", "frequency": "daily", "unit": "USD"},
    "GC=F": {"name": "Gold", "country": "US", "frequency": "daily", "unit": "USD"},
    "HG=F": {"name": "Copper", "country": "US", "frequency": "daily", "unit": "USD"},
    "USDKRW": {"name": "USD/KRW", "country": "KR", "frequency": "daily", "unit": "KRW"},
    "USDJPY": {"name": "USD/JPY", "country": "JP", "frequency": "daily", "unit": "JPY"},
    "EURUSD": {"name": "EUR/USD", "country": "EU", "frequency": "daily", "unit": "USD"},
    "USDCNY": {"name": "USD/CNY", "country": "CN", "frequency": "daily", "unit": "CNY"},
    "USDGBP": {"name": "USD/GBP", "country": "GB", "frequency": "daily", "unit": "GBP"},
    "COPPER_GOLD": {"name": "Copper/Gold Ratio", "country": "GLOBAL", "frequency": "daily", "unit": "ratio"},
    "WTI_BRENT_SPREAD": {"name": "WTI-Brent Spread", "country": "GLOBAL", "frequency": "daily", "unit": "USD"},
    "XLK": {"name": "Technology", "country": "US", "frequency": "daily", "unit": "index"},
    "XLF": {"name": "Financials", "country": "US", "frequency": "daily", "unit": "index"},
    "XLE": {"name": "Energy", "country": "US", "frequency": "daily", "unit": "index"},
    "XLV": {"name": "Health Care", "country": "US", "frequency": "daily", "unit": "index"},
    "XLI": {"name": "Industrials", "country": "US", "frequency": "daily", "unit": "index"},
    "XLY": {"name": "Consumer Discretionary", "country": "US", "frequency": "daily", "unit": "index"},
    "XLP": {"name": "Consumer Staples", "country": "US", "frequency": "daily", "unit": "index"},
    "XLU": {"name": "Utilities", "country": "US", "frequency": "daily", "unit": "index"},
    "XLB": {"name": "Materials", "country": "US", "frequency": "daily", "unit": "index"},
    "XLRE": {"name": "Real Estate", "country": "US", "frequency": "daily", "unit": "index"},
    "XLC": {"name": "Communication", "country": "US", "frequency": "daily", "unit": "index"},
}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    _backfill_legacy_observations(bind, table_names)

    if "observations" in table_names:
        _deduplicate_observations()
        with op.batch_alter_table("observations") as batch_op:
            unique_names = {item["name"] for item in inspector.get_unique_constraints("observations")}
            if "uq_observation_indicator_date_value" in unique_names:
                batch_op.drop_constraint("uq_observation_indicator_date_value", type_="unique")
            if "uq_observation_indicator_date" not in unique_names:
                batch_op.create_unique_constraint("uq_observation_indicator_date", ["indicator_id", "date"])

    for table_name in LEGACY_TABLES:
        if table_name in table_names:
            op.drop_table(table_name)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "observations" in table_names:
        with op.batch_alter_table("observations") as batch_op:
            unique_names = {item["name"] for item in inspector.get_unique_constraints("observations")}
            if "uq_observation_indicator_date" in unique_names:
                batch_op.drop_constraint("uq_observation_indicator_date", type_="unique")
            if "uq_observation_indicator_date_value" not in unique_names:
                batch_op.create_unique_constraint(
                    "uq_observation_indicator_date_value",
                    ["indicator_id", "date", "value"],
                )

    op.create_table(
        "interest_rates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("series_key", sa.String(length=50), nullable=False),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("series_key", "date", name="uq_interest_rates_series_key_date"),
    )
    op.create_index("ix_ir_key_date", "interest_rates", ["series_key", "date"], unique=False)

    op.create_table(
        "macro_indicators",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("series_key", sa.String(length=50), nullable=False),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("series_key", "date", name="uq_macro_indicators_series_key_date"),
    )
    op.create_index("ix_macro_key_date", "macro_indicators", ["series_key", "date"], unique=False)

    op.create_table(
        "exchange_rates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("pair", sa.String(length=20), nullable=False),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pair", "date", name="uq_exchange_rates_pair_date"),
    )
    op.create_index("ix_fx_pair_date", "exchange_rates", ["pair", "date"], unique=False)

    op.create_table(
        "equity_indices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("ticker", sa.String(length=20), nullable=False),
        sa.Column("close", sa.Float(), nullable=True),
        sa.Column("change_1d", sa.Float(), nullable=True),
        sa.Column("change_1d_pct", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker", "date", name="uq_equity_indices_ticker_date"),
    )
    op.create_index("ix_eq_ticker_date", "equity_indices", ["ticker", "date"], unique=False)

    op.create_table(
        "sector_performance",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("ticker", sa.String(length=10), nullable=False),
        sa.Column("sector_name", sa.String(length=50), nullable=True),
        sa.Column("close", sa.Float(), nullable=True),
        sa.Column("change_1d_pct", sa.Float(), nullable=True),
        sa.Column("change_1m_pct", sa.Float(), nullable=True),
        sa.Column("change_3m_pct", sa.Float(), nullable=True),
        sa.Column("change_ytd_pct", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker", "date", name="uq_sector_performance_ticker_date"),
    )
    op.create_index("ix_sec_ticker_date", "sector_performance", ["ticker", "date"], unique=False)

    op.create_table(
        "credit_spreads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("series_key", sa.String(length=50), nullable=False),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("series_key", "date", name="uq_credit_spreads_series_key_date"),
    )
    op.create_index("ix_cs_key_date", "credit_spreads", ["series_key", "date"], unique=False)

    op.create_table(
        "real_economy",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("series_key", sa.String(length=50), nullable=False),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("series_key", "date", name="uq_real_economy_series_key_date"),
    )
    op.create_index("ix_re_key_date", "real_economy", ["series_key", "date"], unique=False)

    op.create_table(
        "sentiment_indicators",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("series_key", sa.String(length=50), nullable=False),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sent_key_date", "sentiment_indicators", ["series_key", "date"], unique=False)


def _deduplicate_observations() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM observations
            WHERE id IN (
                SELECT id
                FROM (
                    SELECT
                        id,
                        ROW_NUMBER() OVER (
                            PARTITION BY indicator_id, date
                            ORDER BY id DESC
                        ) AS row_num
                    FROM observations
                ) ranked
                WHERE ranked.row_num > 1
            )
            """
        )
    )


def _backfill_legacy_observations(bind, table_names: set[str]) -> None:
    if "indicators" not in table_names or "observations" not in table_names:
        return

    indicators_table = sa.Table("indicators", sa.MetaData(), autoload_with=bind)
    observations_table = sa.Table("observations", sa.MetaData(), autoload_with=bind)

    indicator_rows: list[dict[str, object]] = []
    observation_rows: list[dict[str, object]] = []

    for table_name, key_column, value_column, date_column, category, source in LEGACY_BACKFILL_TABLES:
        if table_name not in table_names:
            continue

        rows = bind.execute(
            sa.text(
                f'SELECT "{key_column}" AS series_key, "{date_column}" AS observed_at, "{value_column}" AS observed_value '
                f'FROM "{table_name}" WHERE "{value_column}" IS NOT NULL'
            )
        ).mappings().all()

        for row in rows:
            series_key = _normalize_series_key(str(row["series_key"]))
            metadata = INDICATOR_DEFAULTS.get(series_key, {})
            indicator_rows.append(
                {
                    "code": series_key,
                    "name": metadata.get("name", series_key),
                    "description": None,
                    "country": metadata.get("country", "GLOBAL"),
                    "category": category,
                    "source": source,
                    "frequency": metadata.get("frequency", "daily"),
                    "unit": metadata.get("unit", "value"),
                    "is_active": True,
                }
            )
            observation_rows.append(
                {
                    "series_key": series_key,
                    "date": _coerce_to_date(row["observed_at"]),
                    "value": float(row["observed_value"]),
                }
            )

    if not indicator_rows:
        return

    _upsert_rows(bind, indicators_table, indicator_rows, ["code"])

    indicator_map = {
        row["code"]: row["id"]
        for row in bind.execute(sa.select(indicators_table.c.id, indicators_table.c.code)).mappings()
    }
    normalized_observation_rows = [
        {
            "indicator_id": indicator_map[row["series_key"]],
            "date": row["date"],
            "value": row["value"],
        }
        for row in observation_rows
        if row["series_key"] in indicator_map and row["date"] is not None
    ]
    _upsert_rows(bind, observations_table, normalized_observation_rows, ["indicator_id", "date"])


def _upsert_rows(bind, table, rows: list[dict[str, object]], conflict_columns: list[str]) -> None:
    if not rows:
        return

    dialect_name = bind.dialect.name
    if dialect_name == "postgresql":
        insert_fn = pg_insert
    elif dialect_name == "sqlite":
        insert_fn = sqlite_insert
    else:
        raise ValueError(f"Unsupported upsert dialect: {dialect_name}")

    stmt = insert_fn(table).values(rows)
    update_columns = [
        column.name
        for column in table.columns
        if column.name not in {"id", "created_at"} and column.name not in set(conflict_columns)
    ]
    excluded = stmt.excluded
    bind.execute(
        stmt.on_conflict_do_update(
            index_elements=[table.c[column] for column in conflict_columns],
            set_={column: getattr(excluded, column) for column in update_columns},
        )
    )


def _coerce_to_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value.split(" ")[0])
    return value


def _normalize_series_key(series_key: str) -> str:
    return "^SSEC" if series_key == "000001.SS" else series_key
