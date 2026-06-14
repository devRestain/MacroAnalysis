from __future__ import annotations

from sqlalchemy import inspect, text

from .database import engine

BASELINE_PRE_HARDENING_REVISION = "20260610_0010"
NEWS_SCHEMA_REVISION = "20260610_0011"
CURRENT_REVISION = "20260611_0015"


def bootstrap_alembic_version_if_needed() -> str | None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if not table_names:
        return None

    if "alembic_version" in table_names:
        with engine.connect() as conn:
            existing = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        if existing:
            return existing

    if not _looks_like_application_schema(table_names):
        return None

    revision = _infer_existing_revision(inspector, table_names)
    with engine.begin() as conn:
        if "alembic_version" not in table_names:
            conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"))
        else:
            conn.execute(text("DELETE FROM alembic_version"))
        conn.execute(text("INSERT INTO alembic_version (version_num) VALUES (:revision)"), {"revision": revision})
    return revision


def _looks_like_application_schema(table_names: set[str]) -> bool:
    required = {"indicators", "observations", "signals"}
    return required.issubset(table_names)


def _infer_existing_revision(inspector, table_names: set[str]) -> str:
    if "news_items" in table_names:
        news_columns = {column["name"] for column in inspector.get_columns("news_items")}
        if "url_hash" in news_columns:
            if "change_snapshots" in table_names:
                return CURRENT_REVISION
            return NEWS_SCHEMA_REVISION
    return BASELINE_PRE_HARDENING_REVISION


if __name__ == "__main__":
    revision = bootstrap_alembic_version_if_needed()
    if revision:
        print(f"Bootstrapped Alembic revision: {revision}")
    else:
        print("No Alembic bootstrap needed")
