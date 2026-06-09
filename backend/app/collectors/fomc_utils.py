from __future__ import annotations

import re
from calendar import monthrange
from datetime import datetime


def parse_price(raw) -> float | None:
    if raw in (None, "", "-"):
        return None
    try:
        return float(str(raw).replace(",", ""))
    except ValueError:
        return None


def estimate_policy_probs(current_rate: float, implied_rate: float) -> tuple[float, float, float]:
    """Map a futures-implied rate move to cut/hold/hike probabilities."""
    step = 0.25
    delta = implied_rate - current_rate

    if delta <= -step:
        return 1.0, 0.0, 0.0
    if delta >= step:
        return 0.0, 0.0, 1.0
    if delta < 0:
        cut = min(abs(delta) / step, 1.0)
        return round(cut, 4), round(1.0 - cut, 4), 0.0
    if delta > 0:
        hike = min(delta / step, 1.0)
        return 0.0, round(1.0 - hike, 4), round(hike, 4)
    return 0.0, 1.0, 0.0


MONTH_CODES = {
    1: "F",
    2: "G",
    3: "H",
    4: "J",
    5: "K",
    6: "M",
    7: "N",
    8: "Q",
    9: "U",
    10: "V",
    11: "X",
    12: "Z",
}


def get_fed_funds_futures_symbol(value: datetime) -> str:
    return f"ZQ{MONTH_CODES[value.month]}{value.strftime('%y')}.CBT"


def estimate_next_meeting_move_from_monthly_rates(
    meeting_avg_rate: float,
    anchor_avg_rate: float,
    meeting_date: datetime,
) -> tuple[float, float, float]:
    total_days = monthrange(meeting_date.year, meeting_date.month)[1]
    days_before = meeting_date.day
    days_after = total_days - meeting_date.day
    start_rate = (
        meeting_avg_rate - ((days_after / total_days) * anchor_avg_rate)
    ) / (days_before / total_days)
    return estimate_policy_probs(current_rate=start_rate, implied_rate=anchor_avg_rate)


def parse_meeting_date(month_day: str, year: int) -> datetime:
    """Parse Fed calendar labels like 'January 28-29' as the final meeting day."""
    return parse_meeting_range(month_day, year)[1]


def parse_meeting_range(month_day: str, year: int) -> tuple[datetime, datetime]:
    """Parse Fed calendar labels like 'January 28-29' into start/end datetimes."""
    text = re.sub(r"\s+", " ", month_day.replace("\u2013", "-").replace("\u2014", "-")).strip()
    match = re.match(r"^([A-Za-z]+)\s+(\d{1,2})(?:-(?:[A-Za-z]+\s+)?(\d{1,2}))?", text)
    if not match:
        raise ValueError(f"Unsupported FOMC meeting date label: {month_day}")
    month = match.group(1)
    start_day = match.group(2)
    end_day = match.group(3) or match.group(2)
    start_dt = datetime.strptime(f"{month} {start_day} {year}", "%B %d %Y")
    end_dt = datetime.strptime(f"{month} {end_day} {year}", "%B %d %Y")
    return start_dt, end_dt
