from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ...core.config import settings
from ...core.database import get_db
from ...models import DailyInsight
from ...services.daily_insight_service import (
    daily_insight_to_summary_response,
    ensure_daily_insight,
    get_existing_daily_insight,
    get_today_kst,
)
from ...workers.ai_worker import chat_with_context
from ..ai_schemas import AiChatRequest, AiChatResponse
from ..route_helpers import enqueue_daily_insight_if_missing

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


@router.get("/ai/summary")
async def get_ai_summary(db: Session = Depends(get_db)):
    today_kst = get_today_kst()
    ai = get_existing_daily_insight(db, today_kst)
    if ai and ai.status == "success":
        return daily_insight_to_summary_response(ai)

    latest_success = (
        db.query(DailyInsight)
        .filter(DailyInsight.status == "success")
        .order_by(desc(DailyInsight.as_of_date))
        .first()
    )
    if latest_success:
        enqueue_daily_insight_if_missing()
        return daily_insight_to_summary_response(latest_success)

    enqueue_daily_insight_if_missing()
    ai = get_existing_daily_insight(db, today_kst)
    if not ai:
        raise HTTPException(status_code=404, detail="No AI summary available yet")
    return daily_insight_to_summary_response(ai)


@router.post("/ai/summary/ensure")
async def ensure_ai_summary(
    force: bool = Query(False),
    as_of_date: str | None = None,
    db: Session = Depends(get_db),
):
    try:
        result = ensure_daily_insight(db, as_of_date=as_of_date, force=force)
    except Exception as exc:
        logger.error("Daily insight ensure failed: %s", exc)
        raise HTTPException(status_code=500, detail="Daily insight ensure failed") from exc

    if isinstance(result, dict):
        return result
    return daily_insight_to_summary_response(result)


@router.post("/ai/chat", response_model=AiChatResponse)
async def ai_chat(payload: AiChatRequest, db: Session = Depends(get_db)):
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="AI service not configured")
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")
    try:
        reply = chat_with_context(db, message)
        return {"reply": reply}
    except Exception as exc:
        logger.error("Chat error: %s", exc)
        raise HTTPException(status_code=500, detail="AI chat failed") from exc
