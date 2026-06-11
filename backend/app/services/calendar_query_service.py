from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session
from sqlalchemy import inspect

from ..models import CommunicationEvent, EconomicCalendarEvent, FedWatch

FOMC_EVENT_KEY = "FOMC_MEETING"
FOMC_EVENT_SOURCE = "Federal Reserve"


def has_fedwatch_table(db: Session) -> bool:
    return inspect(db.get_bind()).has_table(FedWatch.__tablename__)


def get_next_fomc_calendar_event(db: Session, now: datetime | None = None) -> EconomicCalendarEvent | None:
    current = now or datetime.now().replace(microsecond=0)
    return (
        db.query(EconomicCalendarEvent)
        .filter(
            EconomicCalendarEvent.event_key == FOMC_EVENT_KEY,
            EconomicCalendarEvent.event_date >= current,
        )
        .order_by(EconomicCalendarEvent.event_date)
        .first()
    )


def get_next_fomc_meeting_date(db: Session, now: datetime | None = None) -> datetime | None:
    event = get_next_fomc_calendar_event(db, now=now)
    if event is not None:
        return event.event_date
    current = now or datetime.now().replace(microsecond=0)
    communication_event = (
        db.query(CommunicationEvent)
        .filter(
            CommunicationEvent.event_type == "fomc_meeting",
            CommunicationEvent.meeting_date >= current,
        )
        .order_by(CommunicationEvent.meeting_date)
        .first()
    )
    return communication_event.meeting_date if communication_event else None


def get_recent_communication_events(
    db: Session,
    *,
    event_type: str | None = None,
    days: int = 30,
    target_key: str | None = None,
) -> list[CommunicationEvent]:
    cutoff = datetime.now().replace(microsecond=0) - __import__("datetime").timedelta(days=days)
    query = db.query(CommunicationEvent).filter(CommunicationEvent.event_date >= cutoff)
    if event_type:
        query = query.filter(CommunicationEvent.event_type == event_type)
    if target_key:
        query = query.filter(CommunicationEvent.title.ilike(f"%{target_key}%"))
    return query.order_by(desc(CommunicationEvent.event_date)).all()


def get_upcoming_fomc_meeting_dates(db: Session, now: datetime | None = None) -> list[datetime]:
    current = now or datetime.now().replace(microsecond=0)
    events = (
        db.query(EconomicCalendarEvent)
        .filter(
            EconomicCalendarEvent.event_key == FOMC_EVENT_KEY,
            EconomicCalendarEvent.event_date >= current,
        )
        .order_by(EconomicCalendarEvent.event_date)
        .all()
    )
    if events:
        return [event.event_date for event in events]

    communication_events = (
        db.query(CommunicationEvent)
        .filter(
            CommunicationEvent.event_type == "fomc_meeting",
            CommunicationEvent.meeting_date >= current,
        )
        .order_by(CommunicationEvent.meeting_date)
        .all()
    )
    return [row.meeting_date for row in communication_events if row.meeting_date is not None]


def get_latest_fedwatch_for_meeting(db: Session, meeting_date: datetime | None) -> FedWatch | None:
    if meeting_date is None or not has_fedwatch_table(db):
        return None
    return (
        db.query(FedWatch)
        .filter(FedWatch.meeting_date == meeting_date)
        .order_by(desc(FedWatch.date))
        .first()
    )


def get_latest_fedwatch(db: Session) -> FedWatch | None:
    if not has_fedwatch_table(db):
        return None
    return db.query(FedWatch).order_by(desc(FedWatch.date)).first()
