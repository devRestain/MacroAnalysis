from __future__ import annotations

from datetime import date, datetime

from sqlalchemy.orm import Session

from ..collectors.calendar_collector import (
    CalendarDefinitionLoader,
    CalendarUpsertService,
    FredReleaseDateLoader,
    RuleBasedMarketCalendarBuilder,
)
from ..collectors.calendar.seed_loader import load_seed_events


def collect_calendar_events(db: Session) -> dict[str, int | str]:
    fetched = 0
    inserted = 0
    reasons: list[str] = []
    definition_loader = CalendarDefinitionLoader()
    definitions_by_key = definition_loader.load_definition_map()
    definitions_by_release_name = definition_loader.load_fred_release_map()
    upsert_service = CalendarUpsertService(db)

    current_year = date.today().year
    rule_builder = RuleBasedMarketCalendarBuilder(definitions_by_key)
    rule_events = rule_builder.build_for_years({current_year, current_year + 1})
    inserted += upsert_service.upsert_many(rule_events)
    fetched += len(rule_events)

    for event in load_seed_events():
        upsert_service.upsert_one(_normalize_seed_event(event, definitions_by_key=definitions_by_key))
        inserted += 1
        fetched += 1

    fred_result = FredReleaseDateLoader(definitions_by_release_name).collect(db, upsert_service)
    for source_result in (fred_result,):
        fetched += int(source_result["fetched_count"])
        inserted += int(source_result["inserted_count"])
        reason = str(source_result.get("reason") or "")
        if source_result["status"] != "success" and reason:
            reasons.append(f"{source_result['job_key']}:{reason}")
    db.commit()
    return {
        "job_key": "calendar_events",
        "status": "success",
        "reason": "ok" if not reasons else ";".join(reasons),
        "fetched_count": fetched,
        "inserted_count": inserted,
        "updated_count": inserted,
    }


def _normalize_seed_event(event: dict, *, definitions_by_key: dict[str, object]) -> dict:
    normalized = dict(event)
    normalized["source"] = normalized.get("source") or "seed"
    if isinstance(normalized.get("event_date"), str):
        normalized["event_date"] = datetime.fromisoformat(normalized["event_date"])
    if isinstance(normalized.get("event_end_date"), str):
        normalized["event_end_date"] = datetime.fromisoformat(normalized["event_end_date"])
    event_key = normalized.get("event_key")
    definition = definitions_by_key.get(event_key)
    if definition is not None:
        normalized.setdefault("display_name", getattr(definition, "display_name", normalized.get("title")))
        normalized.setdefault("short_name", getattr(definition, "short_name", normalized.get("display_name")))
        normalized.setdefault("event_type", getattr(definition, "event_type", normalized.get("event_type")))
        normalized.setdefault("category", getattr(definition, "category", normalized.get("category")))
        normalized.setdefault("importance", getattr(definition, "importance", normalized.get("importance")))
        normalized.setdefault("event_time_local", normalized.get("event_time") or getattr(definition, "default_time", None))
        normalized.setdefault("date_precision", "datetime_estimated" if normalized.get("event_time_local") else "date_only")
        normalized.setdefault("time_source", "static_time_map")
        normalized.setdefault("time_confidence", getattr(definition, "time_confidence", None))
        normalized.setdefault("related_indicator_keys", getattr(definition, "related_indicators", []))
        normalized.setdefault("beginner_description", getattr(definition, "description", None))
        normalized.setdefault("why_it_matters", getattr(definition, "market_role", None))
        normalized.setdefault("watch_items", getattr(definition, "watch_items", []))
        if normalized.get("related_indicator_key") is None and normalized.get("related_indicator_keys"):
            normalized["related_indicator_key"] = normalized["related_indicator_keys"][0]
    normalized.setdefault("event_datetime_utc", normalized.get("event_date"))
    normalized.setdefault("event_date_local", normalized["event_date"].date())
    return normalized
