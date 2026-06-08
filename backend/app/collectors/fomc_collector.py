"""FOMC calendar scraper + CME FedWatch probability parser."""
import logging
import httpx
from datetime import datetime
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..models.indicators import FomcEvent, FedWatch, InterestRate
from .fomc_utils import estimate_policy_probs, parse_meeting_date, parse_price

logger = logging.getLogger(__name__)

FED_CALENDAR_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"


def collect_fomc_calendar(db: Session):
    try:
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            resp = client.get(FED_CALENDAR_URL, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        # Parse meeting dates from the page
        meetings = []
        for row in soup.select(".fomc-meeting"):
            date_str = row.select_one(".fomc-meeting__month")
            if date_str:
                try:
                    # Extract year from header
                    year_header = row.find_previous("h4")
                    year = int(year_header.text.strip()) if year_header else datetime.now().year
                    meeting_dt = parse_meeting_date(date_str.text.strip(), year)
                    meetings.append(meeting_dt)
                except Exception:
                    pass
        for mt in meetings:
            if not db.query(FomcEvent).filter(FomcEvent.meeting_date == mt).first():
                db.add(FomcEvent(meeting_date=mt))
        db.commit()
        logger.info(f"Collected {len(meetings)} FOMC meetings")
    except Exception as e:
        db.rollback()
        logger.error(f"FOMC calendar error: {e}")


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
                logger.warning(f"FedWatch endpoint returned {resp.status_code}, skipping")
                return
            data = resp.json()
        now = datetime.now().replace(microsecond=0)
        next_meeting = db.query(FomcEvent).filter(
            FomcEvent.meeting_date >= now
        ).order_by(FomcEvent.meeting_date).first()
        if not next_meeting:
            return

        quotes = data.get("quotes", [])
        if quotes:
            price = parse_price(quotes[0].get("last"))
            if not price:
                logger.warning("FedWatch quote has no usable last price, skipping")
                return
            implied_rate = 100 - price

            current_rate_row = db.query(InterestRate).filter(
                InterestRate.series_key == "DFF"
            ).order_by(desc(InterestRate.date)).first()
            if not current_rate_row or current_rate_row.value is None:
                logger.warning("No DFF rate available for FedWatch estimate, skipping")
                return

            prob_cut, prob_hold, prob_hike = estimate_policy_probs(
                current_rate=float(current_rate_row.value),
                implied_rate=implied_rate,
            )

            if not db.query(FedWatch).filter(
                FedWatch.date >= now.replace(hour=0, minute=0, second=0),
                FedWatch.meeting_date == next_meeting.meeting_date
            ).first():
                db.add(FedWatch(
                    date=now,
                    meeting_date=next_meeting.meeting_date,
                    prob_hike=prob_hike,
                    prob_hold=prob_hold,
                    prob_cut=prob_cut,
                ))
                db.commit()
        logger.info("Collected FedWatch probabilities")
    except Exception as e:
        db.rollback()
        logger.error(f"FedWatch error: {e}")

