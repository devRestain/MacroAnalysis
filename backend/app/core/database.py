from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import settings

engine_kwargs = {"pool_pre_ping": True}
if not settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update(pool_size=5, max_overflow=10)

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Validate schema state on startup; only dev opt-in may create tables."""
    if settings.DEV_DATABASE_AUTO_INIT:
        _create_all_for_dev()
        return

    expected_revision = _get_alembic_head_revision()
    current_revision = _get_current_alembic_revision()
    if current_revision != expected_revision:
        raise RuntimeError(
            "Database schema is not at Alembic head. "
            f"Current revision: {current_revision!r}, expected: {expected_revision!r}. "
            "Run `alembic upgrade head` before starting the application."
        )


def _create_all_for_dev() -> None:
    with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            conn.execute(text("SELECT pg_advisory_lock(424242)"))
            try:
                Base.metadata.create_all(bind=conn)
            finally:
                conn.execute(text("SELECT pg_advisory_unlock(424242)"))
        else:
            Base.metadata.create_all(bind=conn)


def _get_alembic_head_revision() -> str:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    script = ScriptDirectory.from_config(config)
    return script.get_current_head()


def _get_current_alembic_revision() -> str | None:
    inspector = inspect(engine)
    if "alembic_version" not in inspector.get_table_names():
        return None
    with engine.connect() as conn:
        return conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
