from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...models import NewsItem
from ..route_helpers import news_to_dict

router = APIRouter(prefix="/api")


@router.get("/news")
async def get_news(
    category: str | None = None,
    limit: int = Query(30, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(NewsItem).order_by(desc(NewsItem.published_at))
    if category and category != "all":
        query = query.filter(NewsItem.category == category)
    items = query.limit(limit).all()
    return {"news": [news_to_dict(item) for item in items]}
