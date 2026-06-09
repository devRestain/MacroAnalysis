from __future__ import annotations

from datetime import date, datetime, timedelta

import httpx
from sqlalchemy.orm import Session

from ...core.config import settings
from ...services.calendar_upsert import upsert_calendar_event

FRED_RELEASES_URL = "https://api.stlouisfed.org/fred/releases/dates"

FRED_RELEASE_MAPPING = {
    "Gross Domestic Product": {"event_key": "US_GDP", "category": "growth", "importance": "high"},
    "Advance Monthly Sales for Retail and Food Services": {
        "event_key": "US_RETAIL_SALES",
        "category": "consumption",
        "importance": "high",
    },
}


def collect_fred_release_calendar(db: Session) -> dict[str, int | str]:
    if not settings.CALENDAR_FRED_ENABLED or not settings.FRED_API_KEY:
        return _result("skipped", 0, 0, "calendar_fred_disabled")

    today = date.today()
    params = {
        "api_key": settings.FRED_API_KEY,
        "file_type": "json",
        "realtime_start": today.isoformat(),
        "realtime_end": (today + timedelta(days=settings.CALENDAR_FRED_LOOKAHEAD_DAYS)).isoformat(),
        "include_release_dates_with_no_data": "true",
        "limit": 1000,
    }
    with httpx.Client(timeout=20, follow_redirects=True) as client:
        response = client.get(FRED_RELEASES_URL, params=params)
        response.raise_for_status()
        payload = response.json()

    inserted = 0
    for release in payload.get("release_dates", []):
        mapped = FRED_RELEASE_MAPPING.get(release.get("release_name"))
        if not mapped:
            continue
        event_date = datetime.fromisoformat(release["date"])
        upsert_calendar_event(
            db,
            {
                "event_date": event_date,
                "event_end_date": event_date,
                "event_time": None,
                "timezone": "America/New_York",
                "event_key": mapped["event_key"],
                "event_type": "macro_release",
                "category": mapped["category"],
                "title": release["release_name"],
                "country": "US",
                "source": "FRED",
                "source_url": "https://fred.stlouisfed.org/",
                "importance": mapped["importance"],
                "status": "scheduled",
                "related_indicator_key": None,
                "related_asset": None,
                "metadata_json": {"release_id": release.get("release_id")},
            },
        )
        inserted += 1

    db.commit()
    return _result("success", len(payload.get("release_dates", [])), inserted, None)


def _result(status: str, fetched: int, inserted: int, reason: str | None) -> dict[str, int | str]:
    return {
        "job_key": "calendar_fred",
        "status": status,
        "reason": reason or "ok",
        "fetched_count": fetched,
        "inserted_count": inserted,
        "updated_count": inserted,
    }
