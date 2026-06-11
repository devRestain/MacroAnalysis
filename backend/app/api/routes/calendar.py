from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ...core.cache import cache_get, cache_set
from ...core.database import get_db
from ...models import CommunicationEvent, EconomicCalendarEvent, FedWatch
from ...services.calendar_query_service import get_latest_fedwatch_for_meeting
from ..calendar_schemas import CalendarEventListResponse
from ..route_helpers import calendar_event_to_dict

router = APIRouter(prefix="/api")


@router.get("/calendar/events", response_model=CalendarEventListResponse)
async def get_calendar_events(
    from_date: str | None = Query(None, alias="from"),
    to_date: str | None = Query(None, alias="to"),
    days: int = Query(30, ge=1, le=365),
    category: str | None = None,
    event_type: str | None = None,
    importance: str | None = None,
    country: str = "US",
    include_details: bool = False,
    db: Session = Depends(get_db),
):
    start = datetime.fromisoformat(from_date) if from_date else datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end = datetime.fromisoformat(to_date) + timedelta(days=1) if to_date else start + timedelta(days=days)
    cache_key = (
        f"calendar:events:{start.date().isoformat()}:{end.date().isoformat()}:"
        f"{category}:{event_type}:{importance}:{country}:{include_details}"
    )
    cached = await cache_get(cache_key)
    if cached:
        return cached

    query = db.query(EconomicCalendarEvent).filter(
        EconomicCalendarEvent.event_date >= start,
        EconomicCalendarEvent.event_date < end,
        EconomicCalendarEvent.country == country,
    )
    if category:
        query = query.filter(EconomicCalendarEvent.category == category)
    if event_type:
        query = query.filter(EconomicCalendarEvent.event_type == event_type)
    if importance:
        query = query.filter(EconomicCalendarEvent.importance == importance)

    events = query.order_by(EconomicCalendarEvent.event_date).all()
    payload = {
        "events": [calendar_event_to_dict(event, include_details=include_details) for event in events],
        "count": len(events),
    }
    await cache_set(cache_key, payload, ttl=1800)
    return payload


@router.get("/fomc")
async def get_fomc(db: Session = Depends(get_db)):
    calendar_events = (
        db.query(EconomicCalendarEvent)
        .filter(EconomicCalendarEvent.event_key == "FOMC_MEETING")
        .order_by(EconomicCalendarEvent.event_date)
        .all()
    )
    if calendar_events:
        meetings = [
            {
                "date": str(event.event_date),
                "rate": event.fomc_detail.decision_rate if event.fomc_detail else None,
                "change_bp": event.fomc_detail.change_bp if event.fomc_detail else None,
            }
            for event in calendar_events
        ]
        next_meeting_date = next(
            (event.event_date for event in calendar_events if event.event_date >= datetime.now().replace(microsecond=0)),
            None,
        )
    else:
        legacy_events = (
            db.query(CommunicationEvent)
            .filter(CommunicationEvent.event_type == "fomc_meeting")
            .order_by(CommunicationEvent.meeting_date)
            .all()
        )
        meetings = [
            {"date": str(event.meeting_date), "rate": event.decision_rate, "change_bp": event.change_bp}
            for event in legacy_events
            if event.meeting_date is not None
        ]
        next_meeting_date = next(
            (event.meeting_date for event in legacy_events if event.meeting_date >= datetime.now().replace(microsecond=0)),
            None,
        )

    fedwatch = get_latest_fedwatch_for_meeting(db, next_meeting_date) or db.query(FedWatch).order_by(desc(FedWatch.date)).first()
    return {
        "meetings": meetings,
        "fedwatch": {
            "prob_hold": fedwatch.prob_hold if fedwatch else None,
            "prob_cut": fedwatch.prob_cut if fedwatch else None,
            "prob_hike": fedwatch.prob_hike if fedwatch else None,
            "prob_method": "fed_funds_futures_estimate",
        } if fedwatch else None,
    }
