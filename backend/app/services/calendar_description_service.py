from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


DATA_FILE_NAME = "calendar_event_definitions.json"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_FILE_PATH = DATA_DIR / DATA_FILE_NAME
TOP_LEVEL_KEYS = (
    "schema_version",
    "purpose",
    "language",
    "tone_guidelines",
    "field_definitions",
    "recommended_frontend_usage",
    "recommended_backend_shape",
    "calendar_events",
)


class CalendarDescriptionServiceError(ValueError):
    """Raised when static calendar metadata is missing or malformed."""


def get_calendar_event_definitions_path() -> Path:
    return DATA_FILE_PATH


@lru_cache(maxsize=1)
def load_calendar_event_definitions() -> dict[str, Any]:
    path = get_calendar_event_definitions_path()
    if not path.exists():
        raise CalendarDescriptionServiceError(
            f"Calendar event definitions file not found: {path}"
        )

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CalendarDescriptionServiceError(
            f"Calendar event definitions file is not valid JSON: {path}"
        ) from exc

    validate_calendar_event_definitions_payload(payload)
    return payload


def clear_calendar_event_definitions_cache() -> None:
    load_calendar_event_definitions.cache_clear()


def validate_calendar_event_definitions_payload(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise CalendarDescriptionServiceError(
            "Calendar event definitions payload must be a JSON object."
        )

    for key in TOP_LEVEL_KEYS:
        if key not in payload:
            raise CalendarDescriptionServiceError(
                f"Calendar event definitions payload is missing top-level key: {key}"
            )

    items = payload.get("calendar_events")
    if not isinstance(items, list):
        raise CalendarDescriptionServiceError(
            "Calendar event definitions field `calendar_events` must be a list."
        )

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise CalendarDescriptionServiceError(
                f"Calendar event definitions item `calendar_events[{index}]` must be an object."
            )
        item_key = item.get("key")
        if not isinstance(item_key, str) or not item_key.strip():
            raise CalendarDescriptionServiceError(
                f"Calendar event definitions item `calendar_events[{index}]` is missing a non-empty `key`."
            )
        event_definition = item.get("event_definition")
        if not isinstance(event_definition, dict):
            raise CalendarDescriptionServiceError(
                f"Calendar event definitions item `calendar_events[{index}]` is missing object field `event_definition`."
            )


def list_calendar_event_descriptions(*, enabled_only: bool = False) -> list[dict[str, Any]]:
    payload = load_calendar_event_definitions()
    items = payload["calendar_events"]
    if enabled_only:
        items = [
            item
            for item in items
            if bool((item.get("event_definition") or {}).get("enabled"))
        ]
    return [build_calendar_event_description(item) for item in items]


def get_calendar_event_description(event_key: str) -> dict[str, Any]:
    payload = load_calendar_event_definitions()
    for item in payload["calendar_events"]:
        if item.get("key") == event_key or item.get("event_key") == event_key:
            return build_calendar_event_description(item)
    return _fallback_calendar_event_description(event_key)


def get_related_indicator_keys(event_key: str) -> list[str]:
    return list(get_calendar_event_description(event_key).get("related_indicators") or [])


def get_watch_items(event_key: str) -> list[str]:
    description = get_calendar_event_description(event_key)
    watch_items = description.get("watch_items")
    if isinstance(watch_items, list):
        return list(watch_items)
    analysis_hints = description.get("analysis_hints") or {}
    return list(analysis_hints.get("watch_items") or [])


def get_why_it_matters(event_key: str) -> str | None:
    description = get_calendar_event_description(event_key)
    return description.get("market_role")


def build_calendar_event_description(item: dict[str, Any]) -> dict[str, Any]:
    event_definition = dict(item.get("event_definition") or {})
    description = {
        "key": item.get("key") or item.get("event_key"),
        "event_key": item.get("event_key") or item.get("key"),
        "display_name": item.get("display_name") or item.get("key"),
        "short_name": item.get("short_label") or item.get("display_name") or item.get("key"),
        "short_label": item.get("short_label"),
        "category": item.get("category"),
        "provider": item.get("provider"),
        "description": item.get("description"),
        "market_role": item.get("market_role"),
        "higher_meaning": item.get("higher_meaning"),
        "lower_meaning": item.get("lower_meaning"),
        "watch_points": item.get("watch_points"),
        "watch_items": item.get("watch_items") or (item.get("analysis_hints") or {}).get("watch_items") or [],
        "related_indicators": item.get("related_indicators") or [],
        "workflow_status": item.get("workflow_status"),
        "display_text": item.get("display_text"),
        "analysis_hints": item.get("analysis_hints"),
        "event_definition": event_definition,
        "event_type": event_definition.get("event_type"),
        "importance": event_definition.get("importance"),
        "default_time": event_definition.get("default_time"),
        "timezone": event_definition.get("timezone"),
        "date_source": event_definition.get("date_source"),
        "time_confidence": event_definition.get("time_confidence"),
        "enabled": bool(event_definition.get("enabled")),
        "fred_release_names": event_definition.get("fred_release_names") or [],
        "why_it_matters": item.get("market_role"),
        "beginner_description": item.get("description"),
    }
    return description


def _fallback_calendar_event_description(event_key: str) -> dict[str, Any]:
    return {
        "key": event_key,
        "event_key": event_key,
        "display_name": event_key,
        "short_name": event_key,
        "short_label": event_key,
        "category": "unknown",
        "provider": "unknown",
        "description": None,
        "market_role": None,
        "higher_meaning": None,
        "lower_meaning": None,
        "watch_points": None,
        "watch_items": [],
        "related_indicators": [],
        "workflow_status": {
            "is_runtime_signal": False,
            "is_static_explanation": False,
            "safe_for_display": True,
            "safe_for_scoring": False,
            "fallback": True,
        },
        "display_text": {
            "short_label": event_key,
            "description": None,
            "market_role": None,
            "higher_meaning": None,
            "lower_meaning": None,
            "watch_points": None,
        },
        "analysis_hints": {
            "not_runtime_sentiment": True,
            "not_runtime_expectation": True,
            "requires_runtime_context": True,
            "watch_items": [],
        },
        "event_definition": {
            "event_type": None,
            "importance": None,
            "default_time": None,
            "timezone": "America/New_York",
            "date_source": None,
            "time_confidence": None,
            "enabled": False,
            "fred_release_names": [],
        },
        "event_type": None,
        "importance": None,
        "default_time": None,
        "timezone": "America/New_York",
        "date_source": None,
        "time_confidence": None,
        "enabled": False,
        "fred_release_names": [],
        "why_it_matters": None,
        "beginner_description": None,
    }
