from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..core.upsert import upsert_rows
from ..models import CommunicationEvent


COMMUNICATION_EVENT_UPDATE_COLUMNS = [
    "url",
    "institution",
    "country",
    "content_text",
    "meeting_date",
    "decision_rate",
    "change_bp",
    "statement_url",
    "minutes_url",
    "projection_url",
    "metadata_json",
    "sentiment_status",
    "sentiment_queued_at",
    "sentiment_extracted_at",
]


def upsert_communication_event(db: Session, event: dict[str, Any]) -> CommunicationEvent:
    payload = dict(event)
    payload["source"] = payload.get("source") or "Federal Reserve"
    payload["institution"] = payload.get("institution") or "Federal Reserve"
    payload["country"] = payload.get("country") or "US"
    upsert_rows(
        db,
        CommunicationEvent,
        [payload],
        conflict_columns=["source", "event_type", "event_date", "title"],
        update_columns=COMMUNICATION_EVENT_UPDATE_COLUMNS,
    )
    db.flush()
    return (
        db.query(CommunicationEvent)
        .filter(
            CommunicationEvent.source == payload["source"],
            CommunicationEvent.event_type == payload["event_type"],
            CommunicationEvent.event_date == payload["event_date"],
            CommunicationEvent.title == payload["title"],
        )
        .one()
    )
