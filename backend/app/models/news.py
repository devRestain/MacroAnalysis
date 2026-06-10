from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, Text
from sqlalchemy.sql import func

from ..core.database import Base


class NewsItem(Base):
    __tablename__ = "news_items"

    id = Column(Integer, primary_key=True)
    source = Column(String(100))
    title = Column(Text, nullable=False)
    summary = Column(Text)
    url = Column(Text)
    category = Column(String(50))
    published_at = Column(DateTime)
    collected_at = Column(DateTime, server_default=func.now())
    sentiment_extracted = Column(Boolean, default=False, nullable=False, server_default="false")

    __table_args__ = (
        Index("ix_news_items_published_at", "published_at"),
        Index("ix_news_items_category_published_at", "category", "published_at"),
    )
