from __future__ import annotations

from sqlalchemy import Column, Date, DateTime, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from ..core.database import Base


class AiSummary(Base):
    __tablename__ = "ai_summaries"

    id = Column(Integer, primary_key=True)
    summary_date = Column(DateTime, nullable=False)
    summary_type = Column(String(50), nullable=False, default="macro", server_default="macro")
    target_key = Column(String(128), nullable=True)
    headline = Column(Text)
    body = Column(Text)
    indicators_snapshot = Column(JSON)
    model_used = Column(String(50))
    metadata_json = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_ai_summaries_type_date", "summary_type", "summary_date"),
        Index("ix_ai_summaries_target_date", "target_key", "summary_date"),
        UniqueConstraint("summary_date", "summary_type", "target_key", name="uq_ai_summary_scope"),
    )


class DailyInsight(Base):
    __tablename__ = "daily_insights"

    id = Column(Integer, primary_key=True)
    as_of_date = Column(Date, nullable=False, unique=True)
    model = Column(String(100))
    summary = Column(Text)
    key_points = Column(JSON)
    risks = Column(JSON)
    opportunities = Column(JSON)
    source_observation_max_updated_at = Column(DateTime)
    prompt_hash = Column(String(128))
    status = Column(String(20), nullable=False, default="pending", server_default="pending")
    error_message = Column(Text)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_daily_insights_status_updated_at", "status", "updated_at"),
    )


class IndicatorExplanation(Base):
    __tablename__ = "indicator_explanations"

    id = Column(Integer, primary_key=True)
    indicator_key = Column(String(100), nullable=False, unique=True, index=True)
    display_name = Column(String(255), nullable=False)
    category = Column(String(64), nullable=True)
    provider = Column(String(128), nullable=True)
    description = Column(Text, nullable=True)
    short_label = Column(String(255), nullable=True)
    market_role = Column(Text, nullable=True)
    higher_meaning = Column(Text, nullable=True)
    lower_meaning = Column(Text, nullable=True)
    watch_points = Column(JSON, nullable=True)
    related_indicators = Column(JSON, nullable=True)
    workflow_status = Column(JSON, nullable=True)
    display_text = Column(JSON, nullable=True)
    analysis_hints = Column(JSON, nullable=True)
    source_schema_version = Column(String(32), nullable=False)
    source_file = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
