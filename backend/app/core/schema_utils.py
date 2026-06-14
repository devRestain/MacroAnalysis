from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


def has_table(bind_or_session: Session | Engine, table_name: str) -> bool:
    bind = bind_or_session.get_bind() if isinstance(bind_or_session, Session) else bind_or_session
    return inspect(bind).has_table(table_name)
