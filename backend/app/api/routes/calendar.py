from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...core.cache import cache_get, cache_set
from ...core.database import get_db
from ...models import CommunicationEvent, EconomicCalendarEvent
from ...services.calendar_query_service import get_latest_fedwatch, get_latest_fedwatch_for_meeting
from ...services.localization import localize_calendar_event_dict, localize_fomc_overview_payload, normalize_locale
from ..calendar_schemas import CalendarEventListResponse, CalendarEventResponse

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
    lang: str | None = Query(None),
    db: Session = Depends(get_db),
):
    locale = normalize_locale(lang)
    start = datetime.fromisoformat(from_date) if from_date else datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end = datetime.fromisoformat(to_date) + timedelta(days=1) if to_date else start + timedelta(days=days)
    cache_key = (
        f"calendar:events:{start.date().isoformat()}:{end.date().isoformat()}:"
        f"{category}:{event_type}:{importance}:{country}:{include_details}:{locale}"
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
        "events": [_calendar_event_to_dict(event, include_details=include_details, locale=locale) for event in events],
        "count": len(events),
    }
    await cache_set(cache_key, payload, ttl=1800)
    return payload


@router.get("/calendar/events/{event_id}", response_model=CalendarEventResponse)
async def get_calendar_event_detail(
    event_id: int,
    include_details: bool = True,
    lang: str | None = Query(None),
    db: Session = Depends(get_db),
):
    locale = normalize_locale(lang)
    cache_key = f"calendar:event:{event_id}:{include_details}:{locale}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    event = (
        db.query(EconomicCalendarEvent)
        .filter(EconomicCalendarEvent.id == event_id)
        .first()
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Calendar event not found")

    payload = _calendar_event_to_dict(event, include_details=include_details, locale=locale)
    await cache_set(cache_key, payload, ttl=1800)
    return payload


@router.get("/fomc")
async def get_fomc(lang: str | None = Query(None), db: Session = Depends(get_db)):
    locale = normalize_locale(lang)
    calendar_events = (
        db.query(EconomicCalendarEvent)
        .filter(EconomicCalendarEvent.event_key == "FOMC_MEETING")
        .order_by(EconomicCalendarEvent.event_date)
        .all()
    )
    if calendar_events:
        meetings = [
            {
                "id": event.id,
                "date": str(event.event_date),
                "event_key": event.event_key,
                "display_name": event.display_name or event.title,
                "event_date_local": (event.event_date_local or event.event_date.date()).isoformat(),
                "event_time_local": event.event_time_local or event.event_time,
                "timezone": event.timezone,
                "rate": event.fomc_detail.decision_rate if event.fomc_detail else None,
                "change_bp": event.fomc_detail.change_bp if event.fomc_detail else None,
                "details": _calendar_event_to_dict(event, include_details=True, locale=locale).get("details"),
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

    fedwatch = get_latest_fedwatch_for_meeting(db, next_meeting_date) or get_latest_fedwatch(db)
    payload = {
        "meetings": meetings,
        "fedwatch": {
            "prob_hold": fedwatch.prob_hold if fedwatch else None,
            "prob_cut": fedwatch.prob_cut if fedwatch else None,
            "prob_hike": fedwatch.prob_hike if fedwatch else None,
            "prob_method": "fed_funds_futures_estimate",
        } if fedwatch else None,
    }
    return localize_fomc_overview_payload(payload, locale=locale)


def _calendar_event_to_dict(event: EconomicCalendarEvent, *, include_details: bool, locale: str = "ko") -> dict:
    event_dt = event.event_datetime_utc or event.event_date
    if event_dt.tzinfo is None:
        event_utc = event_dt.replace(tzinfo=timezone.utc).isoformat()
    else:
        event_utc = event_dt.astimezone(timezone.utc).isoformat()

    related_indicator_keys = event.related_indicator_keys
    if related_indicator_keys is None and event.related_indicator_key:
        related_indicator_keys = [event.related_indicator_key]

    payload = {
        "id": event.id,
        "event_date": event.event_date,
        "event_end_date": event.event_end_date,
        "event_time": event.event_time,
        "timezone": event.timezone,
        "event_datetime_utc": event.event_datetime_utc or event.event_date,
        "event_date_local": event.event_date_local or event.event_date.date(),
        "event_time_local": event.event_time_local or event.event_time,
        "display_time": _build_display_time(event.event_time_local or event.event_time, event.timezone),
        "event_key": event.event_key,
        "event_type": event.event_type,
        "category": event.category,
        "title": event.title,
        "display_name": event.display_name or event.title,
        "short_name": event.short_name or event.display_name or event.title,
        "country": event.country,
        "source": event.source,
        "source_url": event.source_url,
        "importance": event.importance,
        "status": event.status,
        "date_precision": event.date_precision or ("datetime_estimated" if (event.event_time_local or event.event_time) else "date_only"),
        "time_source": event.time_source,
        "time_confidence": event.time_confidence,
        "beginner_description": event.beginner_description,
        "why_it_matters": event.why_it_matters,
        "watch_items": event.watch_items,
        "related_indicator_key": event.related_indicator_key,
        "related_indicator_keys": related_indicator_keys,
        "related_asset": event.related_asset,
        "actual_value": event.actual_value,
        "forecast_value": event.forecast_value,
        "previous_value": event.previous_value,
        "unit": event.unit,
        "metadata": {
            **(event.metadata_json or {}),
            "event_local_date": (event.event_date_local or event.event_date.date()).isoformat(),
            "event_utc": event_utc,
        },
        "details": None,
    }
    if include_details and event.fomc_detail is not None:
        payload["details"] = {
            "fomc": {
                "meeting_start_date": event.fomc_detail.meeting_start_date.isoformat() if event.fomc_detail.meeting_start_date else None,
                "meeting_end_date": event.fomc_detail.meeting_end_date.isoformat(),
                "decision_rate": event.fomc_detail.decision_rate,
                "target_rate_lower": event.fomc_detail.target_rate_lower,
                "target_rate_upper": event.fomc_detail.target_rate_upper,
                "change_bp": event.fomc_detail.change_bp,
                "statement_url": event.fomc_detail.statement_url,
                "minutes_url": event.fomc_detail.minutes_url,
                "implementation_note_url": event.fomc_detail.implementation_note_url,
                "press_conference_url": event.fomc_detail.press_conference_url,
                "projection_materials_url": event.fomc_detail.projection_materials_url,
                "has_sep": event.fomc_detail.has_sep,
            }
        }
    return localize_calendar_event_dict(payload, locale=locale)


def _build_display_time(local_time: str | None, timezone_name: str | None) -> str | None:
    if not local_time:
        return None
    tz_label = "ET" if timezone_name == "America/New_York" else timezone_name
    return f"{local_time} {tz_label}".strip()
