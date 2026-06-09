from __future__ import annotations

from datetime import date, datetime

from sqlalchemy.orm import Session

from ..collectors.calendar.bls_calendar import collect_bls_calendar
from ..collectors.calendar.fred_release_calendar import collect_fred_release_calendar
from ..collectors.calendar.rule_based_market_calendar import generate_monthly_opex, generate_triple_witching
from ..collectors.calendar.seed_loader import load_seed_events
from .calendar_upsert import upsert_calendar_event


def collect_calendar_events(db: Session) -> dict[str, int | str]:
    fetched = 0
    inserted = 0
    reasons: list[str] = []

    current_year = date.today().year
    for year in {current_year, current_year + 1}:
        for event in generate_monthly_opex(year) + generate_triple_witching(year):
            upsert_calendar_event(db, event)
            inserted += 1
            fetched += 1

    for event in load_seed_events():
        upsert_calendar_event(db, _normalize_seed_event(event))
        inserted += 1
        fetched += 1

    fred_result = collect_fred_release_calendar(db)
    bls_result = collect_bls_calendar(db)
    for source_result in (fred_result, bls_result):
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


def _normalize_seed_event(event: dict) -> dict:
    normalized = dict(event)
    normalized["source"] = normalized.get("source") or "seed"
    if isinstance(normalized.get("event_date"), str):
        normalized["event_date"] = datetime.fromisoformat(normalized["event_date"])
    if isinstance(normalized.get("event_end_date"), str):
        normalized["event_end_date"] = datetime.fromisoformat(normalized["event_end_date"])
    return normalized
