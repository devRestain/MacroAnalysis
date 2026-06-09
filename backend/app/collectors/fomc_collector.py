"""FOMC calendar scraper + CME FedWatch probability parser."""
import logging
import re
from datetime import datetime, timedelta

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.upsert import upsert_rows
from ..models.calendar import EconomicCalendarEvent, FomcEventDetail
from ..models.indicators import FomcEvent, FedWatch, SentimentSignal
from ..services.calendar_query_service import (
    FOMC_EVENT_KEY,
    FOMC_EVENT_SOURCE,
    get_next_fomc_meeting_date,
    get_upcoming_fomc_meeting_dates,
)
from ..services.calendar_upsert import upsert_calendar_event, upsert_fomc_detail
from .fomc_utils import (
    estimate_next_meeting_move_from_monthly_rates,
    get_fed_funds_futures_symbol,
    parse_meeting_range,
)
from .yfinance_support import download_ticker_frames, normalize_price_history

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
        sentiment_candidates: list[dict[str, object]] = []
        for row in soup.select(".fomc-meeting"):
            month_el = row.select_one(".fomc-meeting__month")
            date_el = row.select_one(".fomc-meeting__date")
            if month_el and date_el:
                try:
                    year_header = row.find_previous("h4")
                    if year_header:
                        match = re.search(r"(20\d{2})", year_header.get_text(" ", strip=True))
                        year = int(match.group(1)) if match else datetime.now().year
                    else:
                        year = datetime.now().year
                    label = f"{month_el.get_text(' ', strip=True)} {date_el.get_text(' ', strip=True)}"
                    meeting_start_dt, meeting_end_dt = parse_meeting_range(label, year)
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
        now = datetime.now().replace(microsecond=0)
        for meeting in meetings:
            meeting_end_dt = meeting["meeting_end_date"]
            fomc_event = db.query(FomcEvent).filter(FomcEvent.meeting_date == meeting_end_dt).first()
            if fomc_event is None:
                fomc_event = FomcEvent(meeting_date=meeting_end_dt)
                db.add(fomc_event)
                db.flush()

            statement_url = meeting["links"].get("statement_url")
            minutes_url = meeting["links"].get("minutes_url")
            if statement_url:
                fomc_event.statement_url = statement_url
            if minutes_url:
                fomc_event.minutes_url = minutes_url

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
                    "status": "released" if meeting_end_dt < now else "scheduled",
                    "related_indicator_key": None,
                    "related_asset": "rates",
                    "metadata_json": {"has_sep": meeting["has_sep"]},
                },
            )
            existing_detail = calendar_event.fomc_detail
            statement_url = statement_url or (existing_detail.statement_url if existing_detail else None)
            minutes_url = minutes_url or (existing_detail.minutes_url if existing_detail else None)
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
                    "statement_url": statement_url,
                    "minutes_url": minutes_url,
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

            sentiment_candidates.append(
                {
                    "fomc_event_id": fomc_event.id,
                    "calendar_event_id": calendar_event.id,
                    "meeting_end_dt": meeting_end_dt,
                    "statement_url": statement_url,
                }
            )

        db.commit()
        queued_sentiment_count = 0
        for candidate in sentiment_candidates:
            if _maybe_queue_fomc_statement_sentiment(
                db,
                fomc_event_id=int(candidate["fomc_event_id"]),
                calendar_event_id=int(candidate["calendar_event_id"]),
                meeting_end_dt=candidate["meeting_end_dt"],
                statement_url=candidate["statement_url"],
                now=now,
            ):
                queued_sentiment_count += 1
        logger.info(f"Collected {len(meetings)} FOMC meetings")
        return {
            "fetched_count": len(meetings),
            "inserted_count": len(meetings),
            "updated_count": len(meetings),
            "queued_sentiment_count": queued_sentiment_count,
        }
    except Exception as e:
        db.rollback()
        logger.error(f"FOMC calendar error: {e}")
        raise RuntimeError(f"FOMC calendar collection failed: {type(e).__name__}: {e}") from e


def collect_fedwatch(db: Session):
    """
    Approximate next-meeting FedWatch-style directional probabilities using CME's
    published methodology and 30-Day Fed Funds futures monthly contracts.
    """
    try:
        now = datetime.now().replace(microsecond=0)
        observation_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        meeting_date = _ensure_next_fomc_meeting_date(db, now=now)
        if not meeting_date:
            raise RuntimeError("FedWatch could not determine next FOMC meeting date")
        anchor_month = _find_next_non_meeting_month(db, meeting_date, now=now)
        if anchor_month is None:
            raise RuntimeError("FedWatch could not find a non-FOMC anchor month")

        meeting_symbol = get_fed_funds_futures_symbol(meeting_date)
        anchor_symbol = get_fed_funds_futures_symbol(anchor_month)
        frames = download_ticker_frames([meeting_symbol, anchor_symbol], period="5d")
        meeting_history = normalize_price_history(frames.get(meeting_symbol))
        anchor_history = normalize_price_history(frames.get(anchor_symbol))
        if meeting_history.empty:
            raise RuntimeError(f"FedWatch meeting-month contract returned no data: {meeting_symbol}")
        if anchor_history.empty:
            raise RuntimeError(f"FedWatch anchor-month contract returned no data: {anchor_symbol}")

        meeting_avg_rate = 100 - float(meeting_history.iloc[-1]["Close"])
        anchor_avg_rate = 100 - float(anchor_history.iloc[-1]["Close"])
        prob_cut, prob_hold, prob_hike = estimate_next_meeting_move_from_monthly_rates(
            meeting_avg_rate=meeting_avg_rate,
            anchor_avg_rate=anchor_avg_rate,
            meeting_date=meeting_date,
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
        logger.info(
            "Collected FedWatch probabilities via CME methodology using %s and %s",
            meeting_symbol,
            anchor_symbol,
        )
        return {
            "fetched_count": 1,
            "inserted_count": 1,
            "updated_count": 1,
        }
    except Exception as e:
        db.rollback()
        logger.error(f"FedWatch error: {e}")
        raise RuntimeError(f"FedWatch collection failed: {type(e).__name__}: {e}") from e


def _ensure_next_fomc_meeting_date(db: Session, *, now: datetime) -> datetime | None:
    meeting_date = get_next_fomc_meeting_date(db, now=now)
    if meeting_date is not None:
        return meeting_date

    logger.info("No FOMC meeting found in DB before FedWatch run, refreshing FOMC calendar")
    collect_fomc_calendar(db)
    return get_next_fomc_meeting_date(db, now=now)


def _find_next_non_meeting_month(db: Session, meeting_date: datetime, *, now: datetime) -> datetime | None:
    meeting_months = {
        (value.year, value.month)
        for value in get_upcoming_fomc_meeting_dates(db, now=now)
    }
    year = meeting_date.year
    month = meeting_date.month + 1
    for _ in range(24):
        if month == 13:
            year += 1
            month = 1
        if (year, month) not in meeting_months:
            return datetime(year, month, 1)
        month += 1
    return None


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


def _maybe_queue_fomc_statement_sentiment(
    db: Session,
    *,
    fomc_event_id: int,
    calendar_event_id: int,
    meeting_end_dt: datetime,
    statement_url: str | None,
    now: datetime,
) -> bool:
    if not settings.SENTIMENT_PIPELINE_ENABLED or not settings.FOMC_SENTIMENT_ENABLED:
        return False
    if not settings.OPENAI_API_KEY:
        return False
    if not statement_url or meeting_end_dt > now:
        return False
    if (now - meeting_end_dt).days > settings.FOMC_SENTIMENT_LOOKBACK_DAYS:
        return False
    fomc_detail = (
        db.query(FomcEventDetail)
        .filter(FomcEventDetail.calendar_event_id == calendar_event_id)
        .first()
    )
    if fomc_detail is not None:
        if fomc_detail.sentiment_status == "success":
            return False
        if (
            fomc_detail.sentiment_status == "pending"
            and fomc_detail.sentiment_queued_at is not None
            and now - fomc_detail.sentiment_queued_at < timedelta(hours=settings.FOMC_SENTIMENT_PENDING_TTL_HOURS)
        ):
            return False
    already_processed = (
        db.query(SentimentSignal.id)
        .filter(
            SentimentSignal.source_type == "fomc",
            SentimentSignal.source_id == fomc_event_id,
        )
        .first()
    )
    if already_processed:
        return False

    try:
        statement_text = _fetch_fomc_statement_text(statement_url)
    except Exception as exc:
        logger.warning("FOMC statement fetch failed for %s: %s", statement_url, exc)
        return False

    if len(statement_text) < settings.FOMC_SENTIMENT_MIN_TEXT_LENGTH:
        logger.info(
            "FOMC statement text too short for sentiment extraction: event_id=%s chars=%s",
            fomc_event_id,
            len(statement_text),
        )
        return False

    try:
        if fomc_detail is not None:
            fomc_detail.sentiment_status = "pending"
            fomc_detail.sentiment_queued_at = now
            db.commit()
        _enqueue_fomc_sentiment_task(fomc_event_id=fomc_event_id, text=statement_text)
    except Exception as exc:
        if fomc_detail is not None:
            fomc_detail.sentiment_status = "failed"
            db.commit()
        logger.warning("FOMC sentiment queue failed for event_id=%s: %s", fomc_event_id, exc)
        return False
    return True


def _fetch_fomc_statement_text(statement_url: str) -> str:
    with httpx.Client(timeout=20, follow_redirects=True) as client:
        resp = client.get(statement_url, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    candidates = []
    for selector in (
        "#article p",
        "article p",
        "main p",
        ".col-xs-12.col-sm-8.col-md-8 p",
        ".col-md-8 p",
    ):
        paragraphs = [
            _normalize_statement_text(node.get_text(" ", strip=True))
            for node in soup.select(selector)
        ]
        paragraphs = [text for text in paragraphs if text]
        if paragraphs:
            candidates.append("\n".join(paragraphs))

    if not candidates:
        paragraphs = [
            _normalize_statement_text(node.get_text(" ", strip=True))
            for node in soup.select("p")
        ]
        paragraphs = [text for text in paragraphs if text]
        if paragraphs:
            candidates.append("\n".join(paragraphs))

    return max(candidates, key=len) if candidates else ""


def _normalize_statement_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _enqueue_fomc_sentiment_task(*, fomc_event_id: int, text: str) -> None:
    from ..workers.sentiment_worker import extract_fomc_sentiment

    extract_fomc_sentiment.delay(fomc_event_id, text)
