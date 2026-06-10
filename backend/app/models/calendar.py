from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class FomcEvent(Base):
    __tablename__ = "fomc_events"

    id = Column(Integer, primary_key=True)
    meeting_date = Column(DateTime, nullable=False, unique=True)
    decision_rate = Column(Float)
    change_bp = Column(Integer)
    statement_url = Column(Text)
    minutes_url = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class FedWatch(Base):
    __tablename__ = "fed_watch"

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    meeting_date = Column(DateTime, nullable=False)
    calendar_event_id = Column(Integer, ForeignKey("economic_calendar_events.id"), nullable=True)
    prob_hike = Column(Float)
    prob_hold = Column(Float)
    prob_cut = Column(Float)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_fw_date_meeting", "date", "meeting_date"),
        UniqueConstraint("meeting_date", "date", name="uq_fed_watch_meeting_date_date"),
    )


class EconomicCalendarEvent(Base):
    __tablename__ = "economic_calendar_events"

    id = Column(Integer, primary_key=True)
    event_date = Column(DateTime, nullable=False)
    event_end_date = Column(DateTime, nullable=True)
    event_time = Column(String(20), nullable=True)
    timezone = Column(String(50), nullable=False, default="America/New_York")

    event_key = Column(String(100), nullable=False)
    event_type = Column(String(50), nullable=False)
    category = Column(String(50), nullable=False)

    title = Column(String(200), nullable=False)
    country = Column(String(20), nullable=False, default="US")
    source = Column(String(100), nullable=False, default="unknown")
    source_url = Column(Text, nullable=True)

    importance = Column(String(20), nullable=False, default="medium")
    status = Column(String(20), nullable=False, default="scheduled")

    related_indicator_key = Column(String(50), nullable=True)
    related_asset = Column(String(50), nullable=True)

    actual_value = Column(Float, nullable=True)
    forecast_value = Column(Float, nullable=True)
    previous_value = Column(Float, nullable=True)
    unit = Column(String(30), nullable=True)

    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    fomc_detail = relationship("FomcEventDetail", back_populates="calendar_event", uselist=False)

    __table_args__ = (
        Index("ix_calendar_date_type", "event_date", "event_type"),
        Index("ix_calendar_key_date", "event_key", "event_date"),
        UniqueConstraint("event_key", "event_date", "source", name="uq_calendar_event_key_date_source"),
    )


class FomcEventDetail(Base):
    __tablename__ = "fomc_event_details"

    id = Column(Integer, primary_key=True)
    calendar_event_id = Column(Integer, ForeignKey("economic_calendar_events.id"), nullable=False, unique=True)

    meeting_start_date = Column(DateTime, nullable=True)
    meeting_end_date = Column(DateTime, nullable=False)
    decision_rate = Column(Float, nullable=True)
    target_rate_lower = Column(Float, nullable=True)
    target_rate_upper = Column(Float, nullable=True)
    change_bp = Column(Integer, nullable=True)

    statement_url = Column(Text, nullable=True)
    minutes_url = Column(Text, nullable=True)
    implementation_note_url = Column(Text, nullable=True)
    press_conference_url = Column(Text, nullable=True)
    projection_materials_url = Column(Text, nullable=True)
    sentiment_status = Column(String(20), nullable=True)
    sentiment_queued_at = Column(DateTime, nullable=True)
    sentiment_extracted_at = Column(DateTime, nullable=True)

    has_sep = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    calendar_event = relationship("EconomicCalendarEvent", back_populates="fomc_detail")
