from __future__ import annotations

from sqlalchemy import Column, Date, DateTime, Index, Integer, JSON, String, Text
from sqlalchemy.sql import func

from ..core.database import Base


class CleanupRun(Base):
    __tablename__ = "cleanup_runs"

    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=False)
    collection_success_logs_deleted = Column(Integer, nullable=False, default=0, server_default="0")
    collection_failure_logs_deleted = Column(Integer, nullable=False, default=0, server_default="0")
    raw_responses_deleted = Column(Integer, nullable=False, default=0, server_default="0")
    debug_logs_deleted = Column(Integer, nullable=False, default=0, server_default="0")
    scheduler_logs_deleted = Column(Integer, nullable=False, default=0, server_default="0")
    result_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_cleanup_runs_started_at", "started_at"),
        Index("ix_cleanup_runs_created_at", "created_at"),
    )


class CollectionRun(Base):
    __tablename__ = "collection_runs"

    id = Column(Integer, primary_key=True)
    job_key = Column(String(100), nullable=False)
    provider = Column(String(100), nullable=False)
    target_date = Column(Date)
    status = Column(String(20), nullable=False)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime)
    min_interval_minutes = Column(Integer, nullable=False)
    fetched_count = Column(Integer, nullable=False, default=0, server_default="0")
    inserted_count = Column(Integer, nullable=False, default=0, server_default="0")
    updated_count = Column(Integer, nullable=False, default=0, server_default="0")
    error_message = Column(Text)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_collection_runs_job_key_started_at", "job_key", "started_at"),
        Index("ix_collection_runs_provider_target_date", "provider", "target_date"),
        Index("ix_collection_runs_status_finished_at", "status", "finished_at"),
    )
