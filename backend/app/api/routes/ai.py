from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...core.config import settings
from ...core.database import get_db
from ..dependencies import require_ai_route_access
from ...services.ai_summary_service import (
    ai_summary_to_dict,
    ensure_ai_summary as ensure_scoped_ai_summary,
    get_latest_ai_summary,
)
from ...services.daily_insight_service import (
    daily_insight_to_summary_response,
    ensure_daily_insight,
)
from ...workers.ai_worker import chat_with_context
from ..ai_schemas import AiChatRequest, AiChatResponse, AiSummaryResponse

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


@router.get("/ai/summary", response_model=AiSummaryResponse)
async def get_ai_summary(
    summary_type: str = Query("macro"),
    target_key: str | None = Query(None),
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    row = get_latest_ai_summary(db, summary_type=summary_type, target_key=target_key, days=days)
    if row is None:
        row = ensure_scoped_ai_summary(db, summary_type=summary_type, target_key=target_key, days=days, force=False)
    return ai_summary_to_dict(row)


@router.post("/ai/summary/ensure")
async def ensure_ai_summary(
    force: bool = Query(False),
    summary_type: str = Query("macro"),
    target_key: str | None = Query(None),
    days: int = Query(7, ge=1, le=90),
    as_of_date: str | None = None,
    db: Session = Depends(get_db),
):
    try:
        if summary_type == "legacy_daily_insight":
            result = ensure_daily_insight(db, as_of_date=as_of_date, force=force)
        else:
            result = ensure_scoped_ai_summary(
                db,
                summary_type=summary_type,
                target_key=target_key,
                days=days,
                force=force,
            )
    except Exception as exc:
        logger.error("Daily insight ensure failed: %s", exc)
        raise HTTPException(status_code=500, detail="Daily insight ensure failed") from exc

    if isinstance(result, dict):
        return result
    if hasattr(result, "summary_type"):
        return ai_summary_to_dict(result)
    return daily_insight_to_summary_response(result)


@router.post("/ai/chat", response_model=AiChatResponse, dependencies=[Depends(require_ai_route_access)])
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
