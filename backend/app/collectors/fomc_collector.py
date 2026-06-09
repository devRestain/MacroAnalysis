"""FOMC calendar scraper + CME FedWatch probability parser."""
import logging
from datetime import datetime

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from ..core.upsert import upsert_rows
from ..models.calendar import EconomicCalendarEvent
from ..models.indicators import FomcEvent, FedWatch
from ..services.calendar_query_service import FOMC_EVENT_KEY, FOMC_EVENT_SOURCE, get_next_fomc_meeting_date
from ..services.calendar_upsert import upsert_calendar_event, upsert_fomc_detail
from ..services.observation_query_service import get_latest_observations
from .fomc_utils import estimate_policy_probs, parse_meeting_range, parse_price

logger = logging.getLogger(__name__)

FED_CALENDAR_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"


def _upsert_fedwatch(
    db: Session,
    observation_date: datetime,
    meeting_date: datetime,
    prob_hike: float,
    prob_hold: float,
    prob_cut: float,
):
    upsert_rows(
        db,
        FedWatch,
        [{
            "date": observation_date,
            "meeting_date": meeting_date,
            "prob_hike": prob_hike,
            "prob_hold": prob_hold,
            "prob_cut": prob_cut,
        }],
        conflict_columns=["meeting_date", "date"],
        update_columns=["prob_hike", "prob_hold", "prob_cut"],
    )


def collect_fomc_calendar(db: Session):
    try:
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            resp = client.get(FED_CALENDAR_URL, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        meetings = []
        for row in soup.select(".fomc-meeting"):
            date_str = row.select_one(".fomc-meeting__month")
            if date_str:
                try:
                    year_header = row.find_previous("h4")
                    year = int(year_header.text.strip()) if year_header else datetime.now().year
                    meeting_start_dt, meeting_end_dt = parse_meeting_range(date_str.text.strip(), year)
                    meetings.append(
                        {
                            "meeting_start_date": meeting_start_dt,
                            "meeting_end_date": meeting_end_dt,
                            "links": _extract_fomc_links(row),
                            "has_sep": _has_sep(row),
                        }
                    )
                except Exception:
                    pass
        for meeting in meetings:
            meeting_end_dt = meeting["meeting_end_date"]
            if not db.query(FomcEvent).filter(FomcEvent.meeting_date == meeting_end_dt).first():
                db.add(FomcEvent(meeting_date=meeting_end_dt))

            calendar_event = upsert_calendar_event(
                db,
                {
                    "event_date": meeting_end_dt,
                    "event_end_date": meeting_end_dt,
                    "event_time": "14:00",
                    "timezone": "America/New_York",
                    "event_key": FOMC_EVENT_KEY,
                    "event_type": "central_bank",
                    "category": "fomc",
                    "title": "FOMC Meeting",
                    "country": "US",
                    "source": FOMC_EVENT_SOURCE,
                    "source_url": FED_CALENDAR_URL,
                    "importance": "high",
                    "status": "released" if meeting_end_dt < datetime.now().replace(microsecond=0) else "scheduled",
                    "related_indicator_key": None,
                    "related_asset": "rates",
                    "metadata_json": {"has_sep": meeting["has_sep"]},
                },
            )
            existing_detail = calendar_event.fomc_detail
            upsert_fomc_detail(
                db,
                {
                    "calendar_event_id": calendar_event.id,
                    "meeting_start_date": meeting["meeting_start_date"],
                    "meeting_end_date": meeting_end_dt,
                    "decision_rate": existing_detail.decision_rate if existing_detail else None,
                    "target_rate_lower": existing_detail.target_rate_lower if existing_detail else None,
                    "target_rate_upper": existing_detail.target_rate_upper if existing_detail else None,
                    "change_bp": existing_detail.change_bp if existing_detail else None,
                    "statement_url": meeting["links"].get("statement_url") or (existing_detail.statement_url if existing_detail else None),
                    "minutes_url": meeting["links"].get("minutes_url") or (existing_detail.minutes_url if existing_detail else None),
                    "implementation_note_url": meeting["links"].get("implementation_note_url") or (existing_detail.implementation_note_url if existing_detail else None),
                    "press_conference_url": meeting["links"].get("press_conference_url") or (existing_detail.press_conference_url if existing_detail else None),
                    "projection_materials_url": meeting["links"].get("projection_materials_url") or (existing_detail.projection_materials_url if existing_detail else None),
                    "has_sep": meeting["has_sep"],
                },
            )

            db.query(FedWatch).filter(
                FedWatch.meeting_date == meeting_end_dt,
                FedWatch.calendar_event_id.is_(None),
            ).update({"calendar_event_id": calendar_event.id}, synchronize_session=False)

        db.commit()
        logger.info(f"Collected {len(meetings)} FOMC meetings")
        return {
            "fetched_count": len(meetings),
            "inserted_count": len(meetings),
            "updated_count": len(meetings),
        }
    except Exception as e:
        db.rollback()
        logger.error(f"FOMC calendar error: {e}")
        raise RuntimeError(f"FOMC calendar collection failed: {type(e).__name__}: {e}") from e


def collect_fedwatch(db: Session):
    """
    Approximate FedWatch-style probabilities from the nearest public Fed Funds
    futures quote and the latest effective Fed Funds rate.

    This deliberately avoids hard-coded probabilities. If the public CME quote is
    unavailable or malformed, the task skips rather than publishing fake odds.
    """
    try:
        url = "https://www.cmegroup.com/CmeWS/mvc/Quotes/Future/305/G"
        with httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                raise RuntimeError(f"FedWatch endpoint returned {resp.status_code}")
            data = resp.json()
        now = datetime.now().replace(microsecond=0)
        observation_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        meeting_date = get_next_fomc_meeting_date(db, now=now)
        if not meeting_date:
            raise RuntimeError("FedWatch could not determine next FOMC meeting date")

        quotes = data.get("quotes", [])
        if quotes:
            price = parse_price(quotes[0].get("last"))
            if not price:
                raise RuntimeError("FedWatch quote has no usable last price")
            implied_rate = 100 - price

            current_rate = get_latest_observations(db, ["DFF"])[0]
            if current_rate["latest_value"] is None:
                raise RuntimeError("FedWatch requires latest DFF observation but none was found")

            prob_cut, prob_hold, prob_hike = estimate_policy_probs(
                current_rate=float(current_rate["latest_value"]),
                implied_rate=implied_rate,
            )

            _upsert_fedwatch(
                db,
                observation_date=observation_date,
                meeting_date=meeting_date,
                prob_hike=prob_hike,
                prob_hold=prob_hold,
                prob_cut=prob_cut,
            )
            calendar_event = (
                db.query(EconomicCalendarEvent)
                .filter(
                    EconomicCalendarEvent.event_key == FOMC_EVENT_KEY,
                    EconomicCalendarEvent.event_date == meeting_date,
                    EconomicCalendarEvent.source == FOMC_EVENT_SOURCE,
                )
                .first()
            )
            if calendar_event:
                db.query(FedWatch).filter(
                    FedWatch.meeting_date == meeting_date,
                    FedWatch.date == observation_date,
                ).update({"calendar_event_id": calendar_event.id}, synchronize_session=False)
            db.commit()
            logger.info("Collected FedWatch probabilities")
            return {
                "fetched_count": 1,
                "inserted_count": 1,
                "updated_count": 1,
            }
        raise RuntimeError("FedWatch endpoint returned no quotes")
    except Exception as e:
        db.rollback()
        logger.error(f"FedWatch error: {e}")
        raise RuntimeError(f"FedWatch collection failed: {type(e).__name__}: {e}") from e


def _extract_fomc_links(row) -> dict[str, str | None]:
    links = {
        "statement_url": None,
        "minutes_url": None,
        "implementation_note_url": None,
        "press_conference_url": None,
        "projection_materials_url": None,
    }
    for anchor in row.select("a[href]"):
        href = anchor.get("href")
        if not href:
            continue
        label = anchor.get_text(" ", strip=True).lower()
        full_url = href if href.startswith("http") else f"https://www.federalreserve.gov{href}"
        if "statement" in label:
            links["statement_url"] = full_url
        elif "minutes" in label:
            links["minutes_url"] = full_url
        elif "implementation note" in label:
            links["implementation_note_url"] = full_url
        elif "press conference" in label:
            links["press_conference_url"] = full_url
        elif "projection materials" in label or "summary of economic projections" in label:
            links["projection_materials_url"] = full_url
    return links


def _has_sep(row) -> bool:
    text = row.get_text(" ", strip=True).lower()
    return "summary of economic projections" in text or "sep" in text
