"""create news_items and change_snapshots tables

Revision ID: 20260611_0015
Revises: 20260611_0014
Create Date: 2026-06-11 12:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260611_0015"
down_revision = "20260611_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "news_items" not in table_names:
        op.create_table(
            "news_items",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("source", sa.String(length=100), nullable=True),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("url", sa.Text(), nullable=True),
            sa.Column("url_hash", sa.String(length=64), nullable=False),
            sa.Column("category", sa.String(length=50), nullable=True),
            sa.Column("published_at", sa.DateTime(), nullable=True),
            sa.Column("collected_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.Column(
                "sentiment_extracted",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("url_hash", name="uq_news_items_url_hash"),
        )
        op.create_index("ix_news_items_url_hash", "news_items", ["url_hash"], unique=False)
        op.create_index("ix_news_items_published_at", "news_items", ["published_at"], unique=False)
        op.create_index(
            "ix_news_items_category_published_at",
            "news_items",
            ["category", "published_at"],
            unique=False,
        )

    if "change_snapshots" not in table_names:
        op.create_table(
            "change_snapshots",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("snapshot_date", sa.DateTime(), nullable=False),
            sa.Column("indicator_key", sa.String(length=80), nullable=False),
            sa.Column("label", sa.String(length=100), nullable=True),
            sa.Column("category", sa.String(length=50), nullable=True),
            sa.Column("current_value", sa.Float(), nullable=True),
            sa.Column("unit", sa.String(length=30), nullable=True),
            sa.Column("delta_1d", sa.Float(), nullable=True),
            sa.Column("delta_1d_pct", sa.Float(), nullable=True),
            sa.Column("delta_1w_pct", sa.Float(), nullable=True),
            sa.Column("delta_1m_pct", sa.Float(), nullable=True),
            sa.Column("delta_3m_pct", sa.Float(), nullable=True),
            sa.Column("z_score_1y", sa.Float(), nullable=True),
            sa.Column("direction", sa.String(length=10), nullable=True),
            sa.Column("signal", sa.String(length=10), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_cs_ikey_date", "change_snapshots", ["indicator_key", "snapshot_date"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "change_snapshots" in table_names:
        index_names = {item["name"] for item in inspector.get_indexes("change_snapshots") if item.get("name")}
        if "ix_cs_ikey_date" in index_names:
            op.drop_index("ix_cs_ikey_date", table_name="change_snapshots")
        op.drop_table("change_snapshots")

    if "news_items" in table_names:
        index_names = {item["name"] for item in inspector.get_indexes("news_items") if item.get("name")}
        if "ix_news_items_category_published_at" in index_names:
            op.drop_index("ix_news_items_category_published_at", table_name="news_items")
        if "ix_news_items_published_at" in index_names:
            op.drop_index("ix_news_items_published_at", table_name="news_items")
        if "ix_news_items_url_hash" in index_names:
            op.drop_index("ix_news_items_url_hash", table_name="news_items")
        op.drop_table("news_items")
