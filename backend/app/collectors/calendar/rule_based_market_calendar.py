from __future__ import annotations

from calendar import monthrange
from datetime import datetime


def generate_monthly_opex(year: int) -> list[dict]:
    events = []
    for month in range(1, 13):
        expiry = _third_friday(year, month)
        events.append(
            {
                "event_date": expiry,
                "event_end_date": expiry,
                "event_time": "16:00",
                "timezone": "America/New_York",
                "event_key": "US_MONTHLY_OPEX",
                "event_type": "market_structure",
                "category": "market_structure",
                "title": "월간 옵션 만기",
                "country": "US",
                "source": "rule_based",
                "source_url": None,
                "importance": "medium",
                "status": "scheduled",
                "related_indicator_key": None,
                "related_asset": "equities",
                "metadata_json": {"rule": "third_friday", "holiday_adjusted": False},
            }
        )
    return events


def generate_triple_witching(year: int) -> list[dict]:
    events = []
    for month in (3, 6, 9, 12):
        expiry = _third_friday(year, month)
        events.append(
            {
                "event_date": expiry,
                "event_end_date": expiry,
                "event_time": "16:00",
                "timezone": "America/New_York",
                "event_key": "US_TRIPLE_WITCHING",
                "event_type": "market_structure",
                "category": "market_structure",
                "title": "분기 동시만기",
                "country": "US",
                "source": "rule_based",
                "source_url": None,
                "importance": "high",
                "status": "scheduled",
                "related_indicator_key": None,
                "related_asset": "equities",
                "metadata_json": {"rule": "third_friday", "holiday_adjusted": False},
            }
        )
    return events


def _third_friday(year: int, month: int) -> datetime:
    friday_count = 0
    for day in range(1, monthrange(year, month)[1] + 1):
        current = datetime(year, month, day)
        if current.weekday() == 4:
            friday_count += 1
            if friday_count == 3:
                return current
    raise ValueError(f"Unable to compute third Friday for {year}-{month:02d}")
