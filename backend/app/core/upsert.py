from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session


def upsert_rows(
    db: Session,
    model,
    rows: Sequence[dict],
    conflict_columns: Sequence[str],
    update_columns: Sequence[str] | None = None,
) -> None:
    """Insert or update rows using the active SQL dialect."""
    if not rows:
        return

    bind = db.get_bind()
    dialect_name = bind.dialect.name
    if dialect_name == "postgresql":
        insert_fn = pg_insert
    elif dialect_name == "sqlite":
        insert_fn = sqlite_insert
    else:
        raise ValueError(f"Unsupported upsert dialect: {dialect_name}")

    table = model.__table__
    stmt = insert_fn(table).values(list(rows))
    if update_columns is None:
        update_columns = [
            column.name
            for column in table.columns
            if column.name not in {"id", "created_at"} and column.name not in set(conflict_columns)
        ]

    excluded = stmt.excluded
    set_values = {column: getattr(excluded, column) for column in update_columns}
    conflict_targets = [table.c[column] for column in conflict_columns]

    db.execute(
        stmt.on_conflict_do_update(
            index_elements=conflict_targets,
            set_=set_values,
        )
    )
