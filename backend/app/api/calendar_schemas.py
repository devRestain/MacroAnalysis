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
    display_time: str | None = None
    event_key: str
    event_type: str
    event_type_label: str | None = None
    category: str
    category_label: str | None = None
    title: str
    display_name: str | None = None
    short_name: str | None = None
    country: str
    source: str | None = None
    source_label: str | None = None
    source_url: str | None = None
    importance: str
    importance_label: str | None = None
    status: str
    status_label: str | None = None
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


class CalendarMonthTopEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    display_name: str
    short_name: str | None = None
    importance: str
    category: str
    event_time_local: str | None = None
    display_time: str | None = None


class CalendarMonthDaySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: date
    in_month: bool
    is_today: bool
    is_weekend: bool
    event_count: int
    high_count: int
    medium_count: int
    categories: list[str]
    top_events: list[CalendarMonthTopEvent]


class CalendarMonthRange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_date: date
    end_date: date
    grid_start_date: date
    grid_end_date: date


class CalendarMonthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    month: str
    today_basis: str
    today_date: date
    range: CalendarMonthRange
    days: list[CalendarMonthDaySummary]
