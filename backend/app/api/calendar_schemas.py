from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class CalendarEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    event_date: datetime
    event_end_date: datetime | None = None
    event_time: str | None = None
    timezone: str
    event_datetime_utc: datetime | None = None
    event_date_local: date | None = None
    event_time_local: str | None = None
    event_key: str
    event_type: str
    category: str
    title: str
    display_name: str | None = None
    short_name: str | None = None
    country: str
    source: str | None = None
    source_url: str | None = None
    importance: str
    status: str
    date_precision: str | None = None
    time_source: str | None = None
    time_confidence: str | None = None
    beginner_description: str | None = None
    why_it_matters: str | None = None
    watch_items: list[str] | None = None
    related_indicator_key: str | None = None
    related_indicator_keys: list[str] | None = None
    related_asset: str | None = None
    actual_value: float | None = None
    forecast_value: float | None = None
    previous_value: float | None = None
    unit: str | None = None
    metadata: dict[str, Any] | None = None
    details: dict[str, Any] | None = None


class CalendarEventListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[CalendarEventResponse]
    count: int
