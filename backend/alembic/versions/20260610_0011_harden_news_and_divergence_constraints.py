"""harden news and divergence report constraints

Revision ID: 20260610_0011
Revises: 20260610_0010
Create Date: 2026-06-10 22:10:00
"""

from __future__ import annotations

import hashlib
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from alembic import op
import sqlalchemy as sa


revision = "20260610_0011"
down_revision = "20260610_0010"
branch_labels = None
depends_on = None


news_items = sa.table(
    "news_items",
    sa.column("id", sa.Integer()),
    sa.column("source", sa.String()),
    sa.column("title", sa.Text()),
    sa.column("url", sa.Text()),
    sa.column("published_at", sa.DateTime()),
    sa.column("url_hash", sa.String(length=64)),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "news_items" in table_names:
        with op.batch_alter_table("news_items") as batch_op:
            columns = {column["name"] for column in inspector.get_columns("news_items")}
            if "url_hash" not in columns:
                batch_op.add_column(sa.Column("url_hash", sa.String(length=64), nullable=True))

        rows = bind.execute(
            sa.select(
                news_items.c.id,
                news_items.c.source,
                news_items.c.title,
                news_items.c.url,
                news_items.c.published_at,
            )
        ).fetchall()
        for row in rows:
            bind.execute(
                news_items.update()
                .where(news_items.c.id == row.id)
                .values(url_hash=_build_news_url_hash(row.source, row.title, row.url, row.published_at))
            )

        _deduplicate_news_items()

        with op.batch_alter_table("news_items") as batch_op:
            batch_op.alter_column("url_hash", existing_type=sa.String(length=64), nullable=False)
            batch_op.create_unique_constraint("uq_news_items_url_hash", ["url_hash"])
            batch_op.create_index("ix_news_items_url_hash", ["url_hash"], unique=False)

    if "divergence_reports" in table_names and "divergence_events" in table_names:
        op.execute(
            sa.text(
                """
                DELETE FROM divergence_reports
                WHERE event_id NOT IN (SELECT id FROM divergence_events)
                """
            )
        )
        with op.batch_alter_table("divergence_reports") as batch_op:
            foreign_keys = {fk["name"] for fk in inspector.get_foreign_keys("divergence_reports") if fk.get("name")}
            if "fk_divergence_reports_event_id" not in foreign_keys:
                batch_op.create_foreign_key(
                    "fk_divergence_reports_event_id",
                    "divergence_events",
                    ["event_id"],
                    ["id"],
                    ondelete="CASCADE",
                )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "divergence_reports" in inspector.get_table_names():
        with op.batch_alter_table("divergence_reports") as batch_op:
            foreign_keys = {fk["name"] for fk in inspector.get_foreign_keys("divergence_reports") if fk.get("name")}
            if "fk_divergence_reports_event_id" in foreign_keys:
                batch_op.drop_constraint("fk_divergence_reports_event_id", type_="foreignkey")

    if "news_items" in inspector.get_table_names():
        with op.batch_alter_table("news_items") as batch_op:
            unique_names = {item["name"] for item in inspector.get_unique_constraints("news_items") if item.get("name")}
            index_names = {item["name"] for item in inspector.get_indexes("news_items") if item.get("name")}
            if "uq_news_items_url_hash" in unique_names:
                batch_op.drop_constraint("uq_news_items_url_hash", type_="unique")
            if "ix_news_items_url_hash" in index_names:
                batch_op.drop_index("ix_news_items_url_hash")
            columns = {column["name"] for column in inspector.get_columns("news_items")}
            if "url_hash" in columns:
                batch_op.drop_column("url_hash")


def _deduplicate_news_items() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM news_items
            WHERE id IN (
                SELECT id
                FROM (
                    SELECT
                        id,
                        ROW_NUMBER() OVER (
                            PARTITION BY url_hash
                            ORDER BY
                                CASE WHEN published_at IS NULL THEN 1 ELSE 0 END,
                                published_at DESC,
                                id DESC
                        ) AS row_num
                    FROM news_items
                ) ranked
                WHERE ranked.row_num > 1
            )
            """
        )
    )


def _build_news_url_hash(source, title, url, published_at) -> str:
    normalized_url = _normalize_news_url(url or "")
    if normalized_url:
        basis = normalized_url
    else:
        basis = f"{(source or '').strip().lower()}|{(title or '').strip().lower()}|{published_at}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def _normalize_news_url(url: str) -> str:
    raw = url.strip()
    if not raw:
        return ""
    parsed = urlsplit(raw)
    query = urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=False)))
    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, query, ""))
