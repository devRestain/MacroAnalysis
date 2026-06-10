from __future__ import annotations

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class ChangeSnapshot(Base):
    __tablename__ = "change_snapshots"

    id = Column(Integer, primary_key=True)
    snapshot_date = Column(DateTime, nullable=False)
    indicator_key = Column(String(80), nullable=False)
    label = Column(String(100))
    category = Column(String(50))
    current_value = Column(Float)
    unit = Column(String(30))
    delta_1d = Column(Float)
    delta_1d_pct = Column(Float)
    delta_1w_pct = Column(Float)
    delta_1m_pct = Column(Float)
    delta_3m_pct = Column(Float)
    z_score_1y = Column(Float)
    direction = Column(String(10))
    signal = Column(String(10))
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_cs_ikey_date", "indicator_key", "snapshot_date"),
    )


class Indicator(Base):
    __tablename__ = "indicators"

    id = Column(Integer, primary_key=True)
    code = Column(String(64), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    country = Column(String(64), nullable=False)
    category = Column(String(64), nullable=False)
    source = Column(String(128), nullable=False)
    frequency = Column(String(32), nullable=False)
    unit = Column(String(32), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    observations = relationship(
        "Observation",
        back_populates="indicator",
        cascade="all, delete-orphan",
    )
    signals = relationship(
        "Signal",
        back_populates="indicator",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_indicator_country_category", "country", "category"),
        Index("ix_indicator_source_frequency", "source", "frequency"),
    )


class Observation(Base):
    __tablename__ = "observations"

    id = Column(Integer, primary_key=True)
    indicator_id = Column(Integer, ForeignKey("indicators.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    value = Column(Float, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    indicator = relationship("Indicator", back_populates="observations")
    signals = relationship("Signal", back_populates="observation")

    __table_args__ = (
        UniqueConstraint("indicator_id", "date", name="uq_observation_indicator_date"),
        Index("ix_observation_indicator_date", "indicator_id", "date"),
    )


class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True)
    indicator_id = Column(Integer, ForeignKey("indicators.id", ondelete="CASCADE"), nullable=False)
    observation_id = Column(Integer, ForeignKey("observations.id", ondelete="SET NULL"))
    signal_date = Column(Date, nullable=False)
    signal_type = Column(String(64), nullable=False)
    signal_level = Column(String(32), nullable=False)
    signal_value = Column(Float)
    summary = Column(Text)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    indicator = relationship("Indicator", back_populates="signals")
    observation = relationship("Observation", back_populates="signals")

    __table_args__ = (
        Index("ix_signal_indicator_date", "indicator_id", "signal_date"),
        Index("ix_signal_type_level", "signal_type", "signal_level"),
    )
