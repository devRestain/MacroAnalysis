"""create indicator observation signal tables

Revision ID: 20260608_0001
Revises:
Create Date: 2026-06-08 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260608_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "indicators",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("country", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("frequency", sa.String(length=32), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(
        "ix_indicator_country_category",
        "indicators",
        ["country", "category"],
        unique=False,
    )
    op.create_index(
        "ix_indicator_source_frequency",
        "indicators",
        ["source", "frequency"],
        unique=False,
    )

    op.create_table(
        "observations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("indicator_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["indicator_id"], ["indicators.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "indicator_id",
            "date",
            "value",
            name="uq_observation_indicator_date_value",
        ),
    )
    op.create_index(
        "ix_observation_indicator_date",
        "observations",
        ["indicator_id", "date"],
        unique=False,
    )

    op.create_table(
        "signals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("indicator_id", sa.Integer(), nullable=False),
        sa.Column("observation_id", sa.Integer(), nullable=True),
        sa.Column("signal_date", sa.Date(), nullable=False),
        sa.Column("signal_type", sa.String(length=64), nullable=False),
        sa.Column("signal_level", sa.String(length=32), nullable=False),
        sa.Column("signal_value", sa.Float(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["indicator_id"], ["indicators.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["observation_id"], ["observations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_signal_indicator_date",
        "signals",
        ["indicator_id", "signal_date"],
        unique=False,
    )
    op.create_index(
        "ix_signal_type_level",
        "signals",
        ["signal_type", "signal_level"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_signal_type_level", table_name="signals")
    op.drop_index("ix_signal_indicator_date", table_name="signals")
    op.drop_table("signals")

    op.drop_index("ix_observation_indicator_date", table_name="observations")
    op.drop_table("observations")

    op.drop_index("ix_indicator_source_frequency", table_name="indicators")
    op.drop_index("ix_indicator_country_category", table_name="indicators")
    op.drop_table("indicators")
