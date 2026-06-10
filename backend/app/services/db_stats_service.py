from __future__ import annotations

import os
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..models import CleanupRun


def get_db_stats(db: Session, *, top_n: int = 5) -> dict:
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        return _get_postgres_db_stats(db, top_n=top_n)
    return _get_generic_db_stats(db, top_n=top_n)


def _get_postgres_db_stats(db: Session, *, top_n: int) -> dict:
    current_db = db.execute(text("SELECT current_database()")).scalar_one()
    database_size_bytes = db.execute(
        text("SELECT pg_database_size(current_database())")
    ).scalar_one()

    table_rows = db.execute(
        text(
            """
            SELECT
                st.relname AS table_name,
                pg_total_relation_size(cls.oid) AS total_size_bytes,
                pg_relation_size(cls.oid) AS table_size_bytes,
                pg_indexes_size(cls.oid) AS index_size_bytes,
                st.n_live_tup::bigint AS row_estimate
            FROM pg_stat_user_tables st
            JOIN pg_class cls ON cls.relname = st.relname
            JOIN pg_namespace ns ON ns.oid = cls.relnamespace
            WHERE ns.nspname = 'public'
            ORDER BY pg_total_relation_size(cls.oid) DESC, st.relname
            """
        )
    ).mappings().all()

    index_rows = db.execute(
        text(
            """
            SELECT
                schemaname,
                relname AS table_name,
                indexrelname AS index_name,
                pg_relation_size(indexrelid) AS index_size_bytes
            FROM pg_stat_user_indexes
            WHERE schemaname = 'public'
            ORDER BY pg_relation_size(indexrelid) DESC, indexrelname
            """
        )
    ).mappings().all()

    latest_cleanup = _get_latest_cleanup_run(db)
    tables = [dict(row) for row in table_rows]
    indexes = [dict(row) for row in index_rows]
    return {
        "dialect": "postgresql",
        "database_name": current_db,
        "database_size_bytes": int(database_size_bytes),
        "table_count": len(tables),
        "tables": tables,
        "largest_tables": tables[:top_n],
        "largest_indexes": indexes[:top_n],
        "latest_cleanup": latest_cleanup,
    }


def _get_generic_db_stats(db: Session, *, top_n: int) -> dict:
    inspector = db.get_bind().dialect
    db_url = str(db.get_bind().engine.url)
    parsed = urlparse(db_url)
    database_name = parsed.path.lstrip("/") or ":memory:"
    database_size_bytes = None
    if parsed.scheme.startswith("sqlite") and database_name not in {":memory:", ""} and os.path.exists(parsed.path):
        database_size_bytes = os.path.getsize(parsed.path)

    table_names = sorted(db.get_bind().dialect.get_table_names(db.connection()))
    tables = []
    for table_name in table_names:
        row_count = db.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar_one()
        tables.append(
            {
                "table_name": table_name,
                "total_size_bytes": None,
                "table_size_bytes": None,
                "index_size_bytes": None,
                "row_estimate": int(row_count),
            }
        )
    tables.sort(key=lambda row: row["row_estimate"], reverse=True)
    return {
        "dialect": inspector.name,
        "database_name": database_name,
        "database_size_bytes": database_size_bytes,
        "table_count": len(tables),
        "tables": tables,
        "largest_tables": tables[:top_n],
        "largest_indexes": [],
        "latest_cleanup": _get_latest_cleanup_run(db),
    }


def _get_latest_cleanup_run(db: Session) -> dict | None:
    bind = db.get_bind()
    if CleanupRun.__tablename__ not in bind.dialect.get_table_names(db.connection()):
        return None
    latest = db.query(CleanupRun).order_by(CleanupRun.id.desc()).first()
    if not latest:
        return None
    return {
        "started_at": latest.started_at.isoformat(),
        "finished_at": latest.finished_at.isoformat(),
        "collection_success_logs_deleted": latest.collection_success_logs_deleted,
        "collection_failure_logs_deleted": latest.collection_failure_logs_deleted,
        "raw_responses_deleted": latest.raw_responses_deleted,
        "debug_logs_deleted": latest.debug_logs_deleted,
        "scheduler_logs_deleted": latest.scheduler_logs_deleted,
    }
