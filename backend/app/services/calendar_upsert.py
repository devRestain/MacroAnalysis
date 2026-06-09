from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..core.upsert import upsert_rows
from ..models.calendar import EconomicCalendarEvent, FomcEventDetail


CALENDAR_UPDATE_COLUMNS = [
    "event_end_date",
    "event_time",
    "timezone",
    "event_type",
    "category",
    "title",
    "country",
    "source_url",
    "importance",
    "status",
    "related_indicator_key",
    "related_asset",
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
