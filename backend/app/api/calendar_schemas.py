from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class CalendarEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    event_date: datetime
    event_end_date: datetime | None = None
    event_time: str | None = None
    timezone: str
    event_key: str
    event_type: str
    category: str
    title: str
    country: str
    source: str | None = None
    source_url: str | None = None
    importance: str
    status: str
    related_indicator_key: str | None = None
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
