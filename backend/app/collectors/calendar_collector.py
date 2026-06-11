from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy.orm import Session

from ..core.config import settings
from ..services.calendar_description_service import list_calendar_event_descriptions
from ..services.calendar_upsert import upsert_calendar_event


FRED_RELEASES_URL = "https://api.stlouisfed.org/fred/releases/dates"


def _normalize_release_name(value: str) -> str:
    return " ".join(value.lower().split())


@dataclass
class CalendarDefinition:
    event_key: str
    display_name: str
    short_name: str
    category: str
    provider: str | None
    description: str | None
    market_role: str | None
    watch_items: list[str]
    related_indicators: list[str]
    event_type: str | None
    importance: str | None
    default_time: str | None
    timezone: str
    date_source: str | None
    time_confidence: str | None
    enabled: bool
    fred_release_names: list[str]


class CalendarDefinitionLoader:
    def load_enabled_definitions(self) -> list[CalendarDefinition]:
        items = list_calendar_event_descriptions(enabled_only=True)
        return [self._to_definition(item) for item in items]

    def load_definition_map(self) -> dict[str, CalendarDefinition]:
        return {
            definition.event_key: definition
            for definition in self.load_enabled_definitions()
        }

    def load_fred_release_map(self) -> dict[str, CalendarDefinition]:
        result: dict[str, CalendarDefinition] = {}
        for definition in self.load_enabled_definitions():
            for release_name in definition.fred_release_names:
                result[_normalize_release_name(release_name)] = definition
        return result

    def _to_definition(self, item: dict[str, Any]) -> CalendarDefinition:
        return CalendarDefinition(
            event_key=item["event_key"],
            display_name=item["display_name"],
            short_name=item["short_name"],
            category=item["category"],
            provider=item.get("provider"),
            description=item.get("description"),
            market_role=item.get("market_role"),
            watch_items=list(item.get("watch_items") or []),
            related_indicators=list(item.get("related_indicators") or []),
            event_type=item.get("event_type"),
            importance=item.get("importance"),
            default_time=item.get("default_time"),
            timezone=item.get("timezone") or "America/New_York",
            date_source=item.get("date_source"),
            time_confidence=item.get("time_confidence"),
            enabled=bool(item.get("enabled")),
            fred_release_names=list(item.get("fred_release_names") or []),
        )


class CalendarUpsertService:
    def __init__(self, db: Session):
        self.db = db

    def upsert_many(self, events: list[dict[str, Any]]) -> int:
        count = 0
        for event in events:
            upsert_calendar_event(self.db, event)
            count += 1
        return count

    def upsert_one(self, event: dict[str, Any]) -> None:
        upsert_calendar_event(self.db, event)


class FredReleaseDateLoader:
    def __init__(self, definitions_by_release_name: dict[str, CalendarDefinition]):
        self.definitions_by_release_name = definitions_by_release_name

    def collect(self, db: Session, upsert_service: CalendarUpsertService) -> dict[str, int | str]:
        if not settings.CALENDAR_FRED_ENABLED or not settings.FRED_API_KEY:
            return self._result("skipped", 0, 0, "calendar_fred_disabled")

        today = date.today()
        params = {
            "api_key": settings.FRED_API_KEY,
            "file_type": "json",
            "realtime_start": today.isoformat(),
            "realtime_end": (today + timedelta(days=settings.CALENDAR_FRED_LOOKAHEAD_DAYS)).isoformat(),
            "include_release_dates_with_no_data": "true",
            "limit": 1000,
        }
        try:
            with httpx.Client(timeout=20, follow_redirects=True) as client:
                response = client.get(FRED_RELEASES_URL, params=params)
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            db.rollback()
            return self._result("failed", 0, 0, f"calendar_fred_error:{type(exc).__name__}")

        fetched = 0
        inserted = 0
        for release in payload.get("release_dates", []):
            fetched += 1
            definition = self.definitions_by_release_name.get(
                _normalize_release_name(release.get("release_name", ""))
            )
            if definition is None:
                continue

            event = self._build_event_payload(definition, release)
            upsert_service.upsert_one(event)
            inserted += 1

        return self._result("success", fetched, inserted, None)

    def _build_event_payload(
        self,
        definition: CalendarDefinition,
        release: dict[str, Any],
    ) -> dict[str, Any]:
        local_dt, utc_dt = _build_event_datetimes(
            date.fromisoformat(release["date"]),
            definition.default_time,
            definition.timezone,
        )
        status = "released" if local_dt < datetime.now() else "scheduled"
        return {
            "event_date": local_dt,
            "event_end_date": local_dt,
            "event_time": definition.default_time,
            "timezone": definition.timezone,
            "event_datetime_utc": utc_dt,
            "event_date_local": local_dt.date(),
            "event_time_local": definition.default_time,
            "event_key": definition.event_key,
            "event_type": definition.event_type or "macro_release",
            "category": definition.category,
            "title": definition.display_name,
            "display_name": definition.display_name,
            "short_name": definition.short_name,
            "country": "US",
            "source": "fred",
            "source_url": "https://fred.stlouisfed.org/",
            "importance": definition.importance or "medium",
            "status": status,
            "date_precision": "datetime_estimated",
            "time_source": "static_time_map",
            "time_confidence": definition.time_confidence or "static_medium",
            "related_indicator_key": definition.related_indicators[0] if definition.related_indicators else None,
            "related_indicator_keys": definition.related_indicators,
            "related_asset": None,
            "beginner_description": definition.description,
            "why_it_matters": definition.market_role,
            "watch_items": definition.watch_items,
            "metadata_json": {
                "release_id": release.get("release_id"),
                "release_name": release.get("release_name"),
                "date_source": definition.date_source,
            },
        }

    def _result(self, status: str, fetched: int, inserted: int, reason: str | None) -> dict[str, int | str]:
        return {
            "job_key": "calendar_fred",
            "status": status,
            "reason": reason or "ok",
            "fetched_count": fetched,
            "inserted_count": inserted,
            "updated_count": inserted,
        }


class RuleBasedMarketCalendarBuilder:
    def __init__(self, definitions_by_event_key: dict[str, CalendarDefinition]):
        self.definitions_by_event_key = definitions_by_event_key

    def build_for_years(self, years: set[int]) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        monthly_def = self.definitions_by_event_key.get("US_MONTHLY_OPEX")
        triple_def = self.definitions_by_event_key.get("US_TRIPLE_WITCHING")
        for year in sorted(years):
            if monthly_def:
                events.extend(
                    self._build_monthly_opex_events(year, monthly_def)
                )
            if triple_def:
                events.extend(
                    self._build_triple_witching_events(year, triple_def)
                )
        return events

    def _build_monthly_opex_events(self, year: int, definition: CalendarDefinition) -> list[dict[str, Any]]:
        return [
            self._build_market_event_payload(definition, _third_friday(year, month))
            for month in range(1, 13)
        ]

    def _build_triple_witching_events(self, year: int, definition: CalendarDefinition) -> list[dict[str, Any]]:
        return [
            self._build_market_event_payload(definition, _third_friday(year, month))
            for month in (3, 6, 9, 12)
        ]

    def _build_market_event_payload(self, definition: CalendarDefinition, event_day: date) -> dict[str, Any]:
        local_dt, utc_dt = _build_event_datetimes(
            event_day,
            definition.default_time,
            definition.timezone,
        )
        return {
            "event_date": local_dt,
            "event_end_date": local_dt,
            "event_time": definition.default_time,
            "timezone": definition.timezone,
            "event_datetime_utc": utc_dt,
            "event_date_local": local_dt.date(),
            "event_time_local": definition.default_time,
            "event_key": definition.event_key,
            "event_type": definition.event_type or "market_structure",
            "category": definition.category,
            "title": definition.display_name,
            "display_name": definition.display_name,
            "short_name": definition.short_name,
            "country": "US",
            "source": "rule_generator",
            "source_url": None,
            "importance": definition.importance or "medium",
            "status": "scheduled",
            "date_precision": "datetime_estimated",
            "time_source": "rule_generator",
            "time_confidence": definition.time_confidence or "static_medium",
            "related_indicator_key": None,
            "related_indicator_keys": definition.related_indicators,
            "related_asset": "equities",
            "beginner_description": definition.description,
            "why_it_matters": definition.market_role,
            "watch_items": definition.watch_items,
            "metadata_json": {
                "date_source": definition.date_source,
                "rule": "third_friday",
                "holiday_adjusted": False,
            },
        }


class FederalReserveFomcLoader:
    def collect(self, db: Session) -> dict[str, Any]:
        from .fomc_collector import collect_fomc_calendar

        return collect_fomc_calendar(db)


def _build_event_datetimes(
    event_day: date,
    local_time_text: str | None,
    timezone_name: str,
) -> tuple[datetime, datetime | None]:
    if local_time_text:
        hour, minute = [int(part) for part in local_time_text.split(":", 1)]
        local_dt = datetime.combine(event_day, time(hour=hour, minute=minute))
        zoned = local_dt.replace(tzinfo=ZoneInfo(timezone_name))
        utc_dt = zoned.astimezone(timezone.utc).replace(tzinfo=None)
        return local_dt, utc_dt
    local_dt = datetime.combine(event_day, time.min)
    return local_dt, None


def _third_friday(year: int, month: int) -> date:
    friday_count = 0
    for day in range(1, monthrange(year, month)[1] + 1):
        current = date(year, month, day)
        if current.weekday() == 4:
            friday_count += 1
            if friday_count == 3:
                return current
    raise ValueError(f"Unable to compute third Friday for {year}-{month:02d}")
