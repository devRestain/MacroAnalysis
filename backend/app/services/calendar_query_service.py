from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..models.calendar import EconomicCalendarEvent
from ..models.indicators import FedWatch, FomcEvent

FOMC_EVENT_KEY = "FOMC_MEETING"
FOMC_EVENT_SOURCE = "Federal Reserve"


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
    legacy = (
        db.query(FomcEvent)
        .filter(FomcEvent.meeting_date >= current)
        .order_by(FomcEvent.meeting_date)
        .first()
    )
    return legacy.meeting_date if legacy else None


def get_latest_fedwatch_for_meeting(db: Session, meeting_date: datetime | None) -> FedWatch | None:
    if meeting_date is None:
        return None
    return (
        db.query(FedWatch)
        .filter(FedWatch.meeting_date == meeting_date)
        .order_by(desc(FedWatch.date))
        .first()
    )
