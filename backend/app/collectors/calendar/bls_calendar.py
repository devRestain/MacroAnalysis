from __future__ import annotations

from datetime import datetime
import logging

import httpx
from sqlalchemy.orm import Session

from ...core.config import settings
from ...services.calendar_upsert import upsert_calendar_event

logger = logging.getLogger(__name__)

BLS_EVENT_MAPPING = {
    "Consumer Price Index": {
        "event_key": "US_CPI",
        "category": "inflation",
        "importance": "high",
        "related_indicator_key": "CPIAUCSL",
    },
    "Employment Situation": {
        "event_key": "US_EMPLOYMENT_SITUATION",
        "category": "labor",
        "importance": "high",
        "related_indicator_key": "UNRATE",
    },
}


def collect_bls_calendar(db: Session) -> dict[str, int | str]:
    if not settings.CALENDAR_BLS_ENABLED:
        return _result("skipped", 0, 0, "calendar_bls_disabled")

    try:
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            response = client.get(
                settings.CALENDAR_BLS_ICS_URL,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
                    ),
                    "Accept": "text/calendar,text/plain;q=0.9,*/*;q=0.8",
                    "Referer": "https://www.bls.gov/schedule/news_release/",
                },
            )
            response.raise_for_status()
        events = _parse_ics_events(response.text)
    except httpx.HTTPStatusError as exc:
        logger.warning("BLS calendar fetch blocked: status=%s url=%s", exc.response.status_code, settings.CALENDAR_BLS_ICS_URL)
        return _result("skipped", 0, 0, f"bls_http_{exc.response.status_code}")
    except Exception as exc:
        logger.warning("BLS calendar fetch failed: %s", exc)
        return _result("failed", 0, 0, str(exc))

    inserted = 0
    for event in events:
        title = event.get("SUMMARY", "")
        mapped = _match_mapping(title)
        if not mapped:
            continue
        event_date = _parse_ics_datetime(event.get("DTSTART"))
        if event_date is None:
            continue
        upsert_calendar_event(
            db,
            {
                "event_date": event_date,
                "event_end_date": event_date,
                "event_time": event_date.strftime("%H:%M") if event_date.hour or event_date.minute else None,
                "timezone": "America/New_York",
                "event_key": mapped["event_key"],
                "event_type": "macro_release",
                "category": mapped["category"],
                "title": title,
                "country": "US",
                "source": "BLS",
                "source_url": settings.CALENDAR_BLS_ICS_URL,
                "importance": mapped["importance"],
                "status": "scheduled",
                "related_indicator_key": mapped.get("related_indicator_key"),
                "related_asset": None,
                "metadata_json": {"description": event.get("DESCRIPTION")},
            },
        )
        inserted += 1

    db.commit()
    return _result("success", len(events), inserted, None)


def _parse_ics_events(ics_text: str) -> list[dict[str, str]]:
    events = []
    current = None
    for raw_line in ics_text.splitlines():
        line = raw_line.strip()
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT":
            if current is not None:
                events.append(current)
            current = None
        elif current is not None and ":" in line:
            key, value = line.split(":", 1)
            current[key.split(";", 1)[0]] = value
    return events


def _parse_ics_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    cleaned = value.rstrip("Z")
    for fmt in ("%Y%m%dT%H%M%S", "%Y%m%d"):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None


def _match_mapping(title: str) -> dict | None:
    for key, mapped in BLS_EVENT_MAPPING.items():
        if key.lower() in title.lower():
            return mapped
    return None


def _result(status: str, fetched: int, inserted: int, reason: str | None) -> dict[str, int | str]:
    return {
        "job_key": "calendar_bls",
        "status": status,
        "reason": reason or "ok",
        "fetched_count": fetched,
        "inserted_count": inserted,
        "updated_count": inserted,
    }
