from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from ..core.upsert import upsert_rows
from ..models.calendar import EconomicCalendarEvent, FomcEventDetail


CALENDAR_UPDATE_COLUMNS = [
    "event_end_date",
    "event_time",
    "timezone",
    "event_datetime_utc",
    "event_date_local",
    "event_time_local",
    "event_type",
    "category",
    "title",
    "display_name",
    "short_name",
    "country",
    "source_url",
    "importance",
    "status",
    "date_precision",
    "time_source",
    "time_confidence",
    "related_indicator_key",
    "related_indicator_keys",
    "related_asset",
    "beginner_description",
    "why_it_matters",
    "watch_items",
    "actual_value",
    "forecast_value",
    "previous_value",
    "unit",
    "metadata_json",
]

FOMC_DETAIL_UPDATE_COLUMNS = [
    "meeting_start_date",
    "meeting_end_date",
    "decision_rate",
    "target_rate_lower",
    "target_rate_upper",
    "change_bp",
    "statement_url",
    "minutes_url",
    "implementation_note_url",
    "press_conference_url",
    "projection_materials_url",
    "sentiment_status",
    "sentiment_queued_at",
    "sentiment_extracted_at",
    "has_sep",
]


def upsert_calendar_event(db: Session, event: dict[str, Any]) -> EconomicCalendarEvent:
    payload = dict(event)
    payload["source"] = payload.get("source") or "unknown"
    _apply_calendar_payload_defaults(payload)
    upsert_rows(
        db,
        EconomicCalendarEvent,
        [payload],
        conflict_columns=["event_key", "event_date", "source"],
        update_columns=CALENDAR_UPDATE_COLUMNS,
    )
    db.flush()
    return (
        db.query(EconomicCalendarEvent)
        .filter(
            EconomicCalendarEvent.event_key == payload["event_key"],
            EconomicCalendarEvent.event_date == payload["event_date"],
            EconomicCalendarEvent.source == payload["source"],
        )
        .one()
    )


def _apply_calendar_payload_defaults(payload: dict[str, Any]) -> None:
    event_dt = payload.get("event_datetime_utc") or payload.get("event_date")
    if isinstance(event_dt, datetime):
        payload.setdefault("event_datetime_utc", event_dt)
        payload.setdefault("event_date", event_dt)
        payload.setdefault("event_date_local", event_dt.date())

    event_time = payload.get("event_time_local") or payload.get("event_time")
    if event_time:
        payload.setdefault("event_time_local", event_time)
        payload.setdefault("event_time", event_time)
        payload.setdefault("date_precision", "datetime_estimated")
    else:
        payload.setdefault("date_precision", "date_only")

    payload.setdefault("time_source", "legacy" if payload.get("event_time") and not payload.get("time_source") else payload.get("time_source"))
    payload.setdefault("time_confidence", "estimated" if payload.get("event_time") and not payload.get("time_confidence") else payload.get("time_confidence"))

    title = payload.get("title")
    payload.setdefault("display_name", title)
    payload.setdefault("short_name", payload.get("display_name"))

    if payload.get("related_indicator_keys") is None and payload.get("related_indicator_key"):
        payload["related_indicator_keys"] = [payload["related_indicator_key"]]

    if payload.get("related_indicator_key") is None and payload.get("related_indicator_keys"):
        related = payload["related_indicator_keys"]
        if isinstance(related, list) and related:
            payload["related_indicator_key"] = related[0]


def upsert_fomc_detail(db: Session, detail: dict[str, Any]) -> FomcEventDetail:
    upsert_rows(
        db,
        FomcEventDetail,
        [detail],
        conflict_columns=["calendar_event_id"],
        update_columns=FOMC_DETAIL_UPDATE_COLUMNS,
    )
    db.flush()
    return (
        db.query(FomcEventDetail)
        .filter(FomcEventDetail.calendar_event_id == detail["calendar_event_id"])
        .one()
    )
