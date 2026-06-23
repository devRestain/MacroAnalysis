from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Date, cast, func
from sqlalchemy.orm import Session

from ...core.cache import cache_get, cache_set
from ...core.database import get_db
from ...models import CommunicationEvent, EconomicCalendarEvent
from ...services.calendar_query_service import get_latest_fedwatch, get_latest_fedwatch_for_meeting
from ...services.localization import localize_calendar_event_dict, localize_fomc_overview_payload, normalize_locale
from ..calendar_schemas import CalendarEventListResponse, CalendarEventResponse, CalendarMonthResponse

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
    explicit_date_window = from_date is not None or to_date is not None
    if explicit_date_window:
        start_local = _parse_date_param(from_date) if from_date else _resolve_today_date("market", None)
        end_local = _parse_date_param(to_date) if to_date else start_local + timedelta(days=days - 1)
        cache_key = (
            f"calendar:events:local:{start_local.isoformat()}:{end_local.isoformat()}:"
            f"{category}:{event_type}:{importance}:{country}:{include_details}:{locale}"
        )
    else:
        start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=days)
        cache_key = (
            f"calendar:events:utc:{start.date().isoformat()}:{end.date().isoformat()}:"
            f"{category}:{event_type}:{importance}:{country}:{include_details}:{locale}"
        )
    cached = await cache_get(cache_key)
    if cached:
        return cached

    local_date_expr = _local_event_date_expr()
    query = db.query(EconomicCalendarEvent).filter(EconomicCalendarEvent.country == country)
    if explicit_date_window:
        query = query.filter(local_date_expr >= start_local, local_date_expr <= end_local)
    else:
        query = query.filter(
            EconomicCalendarEvent.event_date >= start,
            EconomicCalendarEvent.event_date < end,
        )
    if category:
        query = query.filter(EconomicCalendarEvent.category == category)
    if event_type:
        query = query.filter(EconomicCalendarEvent.event_type == event_type)
    if importance:
        query = query.filter(EconomicCalendarEvent.importance == importance)

    events = query.order_by(local_date_expr, EconomicCalendarEvent.event_date).all()
    payload = {
        "events": [_calendar_event_to_dict(event, include_details=include_details, locale=locale) for event in events],
        "count": len(events),
    }
    await cache_set(cache_key, payload, ttl=1800)
    return payload


@router.get("/calendar/month", response_model=CalendarMonthResponse)
async def get_calendar_month(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    category: str | None = None,
    importance: str | None = None,
    country: str = "US",
    today_basis: str = Query("market", pattern="^(market|local)$"),
    today_tz: str | None = None,
    lang: str | None = Query(None),
    db: Session = Depends(get_db),
):
    locale = normalize_locale(lang)
    month_start = _parse_month_key(month)
    month_end = _shift_month(month_start, 1) - timedelta(days=1)
    grid_start = month_start - timedelta(days=(month_start.weekday() + 1) % 7)
    grid_end = month_end + timedelta(days=(6 - ((month_end.weekday() + 1) % 7)))
    if (grid_end - grid_start).days + 1 < 42:
        grid_end += timedelta(days=42 - ((grid_end - grid_start).days + 1))

    today_date = _resolve_today_date(today_basis, today_tz)
    cache_key = (
        f"calendar:month:{month}:{country}:{importance}:{category}:"
        f"{today_basis}:{today_tz}:{locale}"
    )
    cached = await cache_get(cache_key)
    if cached:
        return cached

    local_date_expr = _local_event_date_expr()
    query = db.query(EconomicCalendarEvent).filter(
        EconomicCalendarEvent.country == country,
        local_date_expr >= grid_start,
        local_date_expr <= grid_end,
    )
    if category:
        query = query.filter(EconomicCalendarEvent.category == category)
    if importance:
        query = query.filter(EconomicCalendarEvent.importance == importance)

    events = query.order_by(local_date_expr, EconomicCalendarEvent.event_date).all()
    grouped: dict[str, list[EconomicCalendarEvent]] = {}
    for event in events:
        bucket = _event_local_date(event).isoformat()
        grouped.setdefault(bucket, []).append(event)

    days = []
    cursor = grid_start
    while cursor <= grid_end:
        day_events = grouped.get(cursor.isoformat(), [])
        days.append({
            "date": cursor.isoformat(),
            "in_month": cursor.month == month_start.month,
            "is_today": cursor == today_date,
            "is_weekend": cursor.weekday() in {5, 6},
            "event_count": len(day_events),
            "high_count": sum(1 for event in day_events if event.importance == "high"),
            "medium_count": sum(1 for event in day_events if event.importance == "medium"),
            "categories": sorted({event.category for event in day_events}),
            "top_events": [_month_top_event_payload(event, locale=locale) for event in day_events[:3]],
        })
        cursor += timedelta(days=1)

    payload = {
        "month": month,
        "today_basis": today_basis,
        "today_date": today_date.isoformat(),
        "range": {
            "start_date": month_start.isoformat(),
            "end_date": month_end.isoformat(),
            "grid_start_date": grid_start.isoformat(),
            "grid_end_date": grid_end.isoformat(),
        },
        "days": days,
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


def _local_event_date_expr():
    return func.coalesce(EconomicCalendarEvent.event_date_local, cast(EconomicCalendarEvent.event_date, Date))


def _event_local_date(event: EconomicCalendarEvent) -> date:
    return event.event_date_local or event.event_date.date()


def _month_top_event_payload(event: EconomicCalendarEvent, *, locale: str) -> dict:
    payload = _calendar_event_to_dict(event, include_details=False, locale=locale)
    return {
        "id": payload["id"],
        "display_name": payload["display_name"],
        "short_name": payload["short_name"],
        "importance": payload["importance"],
        "category": payload["category"],
        "event_time_local": payload["event_time_local"],
        "display_time": payload["display_time"],
    }


def _parse_month_key(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m").date().replace(day=1)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid month format, expected YYYY-MM") from exc


def _shift_month(value: date, delta: int) -> date:
    month_index = (value.year * 12 + value.month - 1) + delta
    year = month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def _parse_date_param(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        try:
            return datetime.fromisoformat(value).date()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid date format, expected ISO date") from exc


def _resolve_today_date(today_basis: str, today_tz: str | None) -> date:
    timezone_name = "America/New_York"
    if today_basis == "local" and today_tz:
        timezone_name = today_tz
    try:
        now = datetime.now(ZoneInfo(timezone_name))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid timezone: {timezone_name}") from exc
    return now.date()
