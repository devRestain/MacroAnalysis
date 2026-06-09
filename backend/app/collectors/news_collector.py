"""News collector — Finnhub market news + Fed RSS feed."""
import logging
import feedparser
import httpx
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from ..core.config import settings
from ..models.indicators import NewsItem
from .result_utils import empty_counts

logger = logging.getLogger(__name__)

FINNHUB_CATEGORIES = ["general", "forex", "merger"]

KEYWORD_CATEGORY_MAP = {
    "fed": "fed", "fomc": "fed", "federal reserve": "fed", "powell": "fed",
    "rate": "fed", "interest": "fed",
    "cpi": "macro", "inflation": "macro", "pmi": "macro", "gdp": "macro",
    "unemployment": "macro", "jobs": "macro", "payroll": "macro",
    "dollar": "fx", "euro": "fx", "yen": "fx", "forex": "fx", "currency": "fx",
    "recession": "macro", "growth": "macro",
    "oil": "commodity", "gold": "commodity", "copper": "commodity",
    "china": "geopolitics", "war": "geopolitics", "sanction": "geopolitics",
}

FED_RSS_URL = "https://www.federalreserve.gov/feeds/press_all.xml"


def categorize(title: str, summary: str = "") -> str:
    text = (title + " " + summary).lower()
    for keyword, category in KEYWORD_CATEGORY_MAP.items():
        if keyword in text:
            return category
    return "general"


def collect_finnhub_news(db: Session):
    if not settings.FINNHUB_API_KEY:
        logger.warning("FINNHUB_API_KEY not set, skipping")
        return {
            "fetched_count": 0,
            "inserted_count": 0,
            "updated_count": 0,
            "reason": "finnhub_api_key_missing",
        }
    base_url = "https://finnhub.io/api/v1/news"
    counts = empty_counts()
    errors: list[str] = []
    with httpx.Client(timeout=15) as client:
        for cat in FINNHUB_CATEGORIES:
            try:
                resp = client.get(base_url, params={"category": cat, "token": settings.FINNHUB_API_KEY})
                resp.raise_for_status()
                items = resp.json()[:20]
                counts["fetched_count"] += len(items)
                for item in items:
                    url = item.get("url", "")
                    if db.query(NewsItem).filter(NewsItem.url == url).first():
                        continue
                    pub = datetime.fromtimestamp(item.get("datetime", 0), tz=timezone.utc).replace(tzinfo=None)
                    title = item.get("headline", "")
                    summary = item.get("summary", "")
                    db.add(NewsItem(
                        source=item.get("source", "Finnhub"),
                        title=title,
                        summary=summary[:500] if summary else None,
                        url=url,
                        category=categorize(title, summary),
                        published_at=pub,
                    ))
                    counts["inserted_count"] += 1
                    counts["updated_count"] += 1
                db.commit()
                logger.info(f"Collected Finnhub news: {cat}")
            except Exception as e:
                db.rollback()
                logger.error(f"Finnhub news error ({cat}): {e}")
                errors.append(f"{cat}:{type(e).__name__}")
    if counts["fetched_count"] == 0 and errors:
        raise RuntimeError(f"Finnhub news collection failed for all categories: {', '.join(errors[:3])}")
    return counts


def collect_fed_rss(db: Session):
    try:
        feed = feedparser.parse(FED_RSS_URL)
        counts = empty_counts()
        counts["fetched_count"] = len(feed.entries[:15])
        for entry in feed.entries[:15]:
            url = entry.get("link", "")
            if db.query(NewsItem).filter(NewsItem.url == url).first():
                continue
            try:
                pub = datetime(*entry.published_parsed[:6])
            except Exception:
                pub = datetime.now()
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            db.add(NewsItem(
                source="Federal Reserve",
                title=title,
                summary=summary[:500] if summary else None,
                url=url,
                category="fed",
                published_at=pub,
            ))
            counts["inserted_count"] += 1
            counts["updated_count"] += 1
        db.commit()
        logger.info("Collected Fed RSS feed")
        return counts
    except Exception as e:
        db.rollback()
        logger.error(f"Fed RSS error: {e}")
        raise RuntimeError(f"Fed RSS collection failed: {type(e).__name__}: {e}") from e
