from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from ..core.config import settings
from ..models import CommunicationEvent, SentimentSignal
from ..services.communication_event_service import upsert_communication_event
from .result_utils import empty_counts

logger = logging.getLogger(__name__)

FED_SPEECHES_RSS_URL = "https://www.federalreserve.gov/feeds/speeches_and_testimony.xml"


def collect_fed_communications(db: Session):
    try:
        import feedparser
    except Exception as exc:
        raise RuntimeError(f"Fed communications collection requires feedparser: {exc}") from exc

    feed = feedparser.parse(FED_SPEECHES_RSS_URL)
    counts = empty_counts()
    entries = list(feed.entries[:20])
    counts["fetched_count"] = len(entries)
    now = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)

    for entry in entries:
        published_at = _entry_datetime(entry) or now
        title = entry.get("title", "").strip() or "Federal Reserve communication"
        url = entry.get("link", "").strip() or None
        content_text = _fetch_communication_text(url) if url else (entry.get("summary", "") or "")
        event = upsert_communication_event(
            db,
            {
                "event_date": published_at,
                "source": "Federal Reserve",
                "title": title,
                "event_type": _infer_event_type(title, url),
                "url": url,
                "institution": "Federal Reserve",
                "country": "US",
                "content_text": content_text[:12000] if content_text else None,
                "metadata_json": {"feed": "speeches_and_testimony"},
            },
        )
        counts["inserted_count"] += 1
        counts["updated_count"] += 1
        _maybe_queue_communication_sentiment(db, communication_event=event, now=now)

    db.commit()
    logger.info("Collected %s Federal Reserve communication events", len(entries))
    return counts


def _entry_datetime(entry) -> datetime | None:
    if getattr(entry, "published_parsed", None):
        try:
            return datetime(*entry.published_parsed[:6])
        except Exception:
            return None
    if entry.get("published"):
        try:
            return parsedate_to_datetime(entry["published"]).replace(tzinfo=None)
        except Exception:
            return None
    return None


def _infer_event_type(title: str, url: str | None) -> str:
    text = f"{title} {url or ''}".lower()
    if "testimony" in text or "congress" in text:
        return "testimony"
    if "statement" in text:
        return "statement"
    if "speech" in text:
        return "speech"
    return "communication"


def _fetch_communication_text(url: str) -> str:
    with httpx.Client(timeout=20, follow_redirects=True) as client:
        response = client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    paragraphs = [node.get_text(" ", strip=True) for node in soup.select("p")]
    cleaned = [" ".join(part.split()) for part in paragraphs if part and part.strip()]
    return "\n".join(cleaned)


def _maybe_queue_communication_sentiment(
    db: Session,
    *,
    communication_event: CommunicationEvent,
    now: datetime,
) -> bool:
    if not settings.SENTIMENT_PIPELINE_ENABLED or not settings.OPENAI_API_KEY:
        return False
    if not communication_event.content_text:
        return False
    if len(communication_event.content_text) < settings.FOMC_SENTIMENT_MIN_TEXT_LENGTH:
        return False
    if communication_event.sentiment_status == "success":
        return False
    if (
        communication_event.sentiment_status == "pending"
        and communication_event.sentiment_queued_at is not None
        and now - communication_event.sentiment_queued_at < timedelta(hours=settings.FOMC_SENTIMENT_PENDING_TTL_HOURS)
    ):
        return False
    existing = (
        db.query(SentimentSignal.id)
        .filter(
            SentimentSignal.source_type == "communication_event",
            SentimentSignal.source_id == communication_event.id,
        )
        .first()
    )
    if existing:
        return False

    communication_event.sentiment_status = "pending"
    communication_event.sentiment_queued_at = now
    db.flush()
    try:
        from ..workers.sentiment_worker import extract_communication_event_sentiment

        extract_communication_event_sentiment.delay(communication_event.id, communication_event.content_text)
        return True
    except Exception as exc:
        logger.warning("Communication sentiment queue failed for event_id=%s: %s", communication_event.id, exc)
        communication_event.sentiment_status = "failed"
        db.flush()
        return False
