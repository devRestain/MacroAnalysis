from __future__ import annotations

import hashlib
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, Text, UniqueConstraint, event
from sqlalchemy.sql import func

from ..core.database import Base


class NewsItem(Base):
    __tablename__ = "news_items"

    id = Column(Integer, primary_key=True)
    source = Column(String(100))
    title = Column(Text, nullable=False)
    summary = Column(Text)
    url = Column(Text)
    url_hash = Column(String(64), nullable=False)
    category = Column(String(50))
    published_at = Column(DateTime)
    collected_at = Column(DateTime, server_default=func.now())
    sentiment_extracted = Column(Boolean, default=False, nullable=False, server_default="false")

    __table_args__ = (
        UniqueConstraint("url_hash", name="uq_news_items_url_hash"),
        Index("ix_news_items_url_hash", "url_hash"),
        Index("ix_news_items_published_at", "published_at"),
        Index("ix_news_items_category_published_at", "category", "published_at"),
    )


def build_news_url_hash(*, source: str | None, title: str | None, url: str | None, published_at) -> str:
    normalized_url = normalize_news_url(url or "")
    if normalized_url:
        basis = normalized_url
    else:
        basis = f"{(source or '').strip().lower()}|{(title or '').strip().lower()}|{published_at}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def normalize_news_url(url: str) -> str:
    raw = url.strip()
    if not raw:
        return ""
    parsed = urlsplit(raw)
    query = urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=False)))
    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, query, ""))


@event.listens_for(NewsItem, "before_insert")
@event.listens_for(NewsItem, "before_update")
def _populate_url_hash(mapper, connection, target: NewsItem) -> None:
    if not target.url_hash:
        target.url_hash = build_news_url_hash(
            source=target.source,
            title=target.title,
            url=target.url,
            published_at=target.published_at,
        )
