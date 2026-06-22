from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class IndicatorExplanationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    indicator_key: str
    display_name: str
    category: str | None = None
    category_label: str | None = None
    provider: str | None = None
    provider_label: str | None = None
    description: str | None = None
    short_label: str | None = None
    market_role: str | None = None
    higher_meaning: str | None = None
    lower_meaning: str | None = None
    watch_points: Any | None = None
    related_indicators: list[str] | None = None
    display_text: dict[str, Any] | None = None
    workflow_status: dict[str, Any] | None = None
    analysis_hints: dict[str, Any] | None = None
    source_schema_version: str


class IndicatorExplanationListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    indicator_explanations: list[IndicatorExplanationResponse]
    count: int
