from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from ..core.database import Base


class SentimentSignal(Base):
    __tablename__ = "sentiment_signals"

    id = Column(Integer, primary_key=True)
    source_type = Column(String(20), nullable=False)
    source_id = Column(Integer, nullable=False)
    extracted_at = Column(DateTime, server_default=func.now())
    batch_date = Column(DateTime, nullable=False)
    actor = Column(String(30), nullable=False)
    dimension = Column(String(30), nullable=False)
    stance = Column(String(30), nullable=False)
    stance_score = Column(Float, nullable=False)
    intensity = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    evidence = Column(Text)

    __table_args__ = (
        Index("ix_ss_batch_actor_dim", "batch_date", "actor", "dimension"),
        Index("ix_ss_source", "source_type", "source_id"),
        UniqueConstraint(
            "source_type",
            "source_id",
            "batch_date",
            "actor",
            "dimension",
            "stance",
            name="uq_sentiment_signal_source_batch_actor_dimension_stance",
        ),
    )


class Expectation(Base):
    __tablename__ = "expectations"

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    actor = Column(String(30), nullable=False)
    dimension = Column(String(30), nullable=False)
    consensus_score = Column(Float, nullable=False)
    raw_score = Column(Float, nullable=False)
    consensus_strength = Column(Float, nullable=False)
    inertia_age_days = Column(Float, default=0.0)
    inertia_coefficient = Column(Float, default=0.0)
    inertia_reset = Column(Boolean, default=False)
    consensus_7d_ago = Column(Float)
    momentum_score = Column(Float)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_exp_date_actor_dim", "date", "actor", "dimension"),
        UniqueConstraint("date", "actor", "dimension", name="uq_expectation_date_actor_dimension"),
    )


class DivergenceEvent(Base):
    __tablename__ = "divergence_events"

    id = Column(Integer, primary_key=True)
    detected_at = Column(DateTime, server_default=func.now())
    batch_date = Column(DateTime, nullable=False)
    actor = Column(String(30), nullable=False)
    dimension = Column(String(30), nullable=False)
    raw_score = Column(Float, nullable=False)
    consensus_score = Column(Float, nullable=False)
    consensus_strength = Column(Float, nullable=False)
    adjusted_gap = Column(Float, nullable=False)
    severity = Column(String(10), nullable=False)
    inertia_coefficient = Column(Float)
    inertia_reset = Column(Boolean, default=False)
    momentum_score = Column(Float)
    momentum_sign_change = Column(Boolean, default=False)
    multiplier_applied = Column(Float, default=1.0)
    report_generated = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_de_batch_severity", "batch_date", "severity"),
        Index("ix_de_actor_dim", "actor", "dimension"),
        UniqueConstraint("batch_date", "actor", "dimension", name="uq_divergence_event_batch_actor_dimension"),
    )


class DivergenceReport(Base):
    __tablename__ = "divergence_reports"

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("divergence_events.id", ondelete="CASCADE"), nullable=False)
    generated_at = Column(DateTime, server_default=func.now())
    headline = Column(Text, nullable=False)
    background = Column(Text)
    evidence = Column(Text)
    action_plan = Column(Text)
    risk_scenario = Column(Text)
    notified = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_dr_event_id", "event_id"),
        UniqueConstraint("event_id", name="uq_divergence_report_event_id"),
    )
