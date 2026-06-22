from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...services.localization import localize_indicator_explanation_dict, normalize_locale
from ...services.indicator_explanation_query_service import get_indicator_explanation, list_indicator_explanations
from ...services.observation_query_service import adapt_history_to_chart_response, get_observation_history
from ..indicator_schemas import IndicatorExplanationListResponse, IndicatorExplanationResponse

router = APIRouter(prefix="/api")


@router.get("/indicator-explanations", response_model=IndicatorExplanationListResponse)
async def get_indicator_explanations(category: str | None = None, lang: str | None = Query(None), db: Session = Depends(get_db)):
    locale = normalize_locale(lang)
    rows = list_indicator_explanations(db, category=category)
    return {"indicator_explanations": [localize_indicator_explanation_dict(row, locale=locale) for row in rows], "count": len(rows)}


@router.get("/indicator-explanations/{indicator_key}", response_model=IndicatorExplanationResponse)
async def get_indicator_explanation_detail(indicator_key: str, lang: str | None = Query(None), db: Session = Depends(get_db)):
    locale = normalize_locale(lang)
    row = get_indicator_explanation(db, indicator_key)
    if row is None:
        raise HTTPException(status_code=404, detail="Indicator explanation not found")
    return localize_indicator_explanation_dict(row, locale=locale)


@router.get("/chart/{indicator_key}")
async def get_chart(
    indicator_key: str,
    period: str = Query("3m", regex="^(1w|1m|3m|1y|all)$"),
    db: Session = Depends(get_db),
):
    period_days = {"1w": 7, "1m": 30, "3m": 90, "1y": 365, "all": 3650}
    cutoff = datetime.now() - timedelta(days=period_days[period])
    history = get_observation_history(db, indicator_key, start_date=cutoff.date(), limit=500)
    history["period"] = period
    return adapt_history_to_chart_response(history)


@router.get("/indicators/history/{indicator_key}")
async def get_indicator_history(
    indicator_key: str,
    period: str = Query("3m", regex="^(1w|1m|3m|1y|all)$"),
    db: Session = Depends(get_db),
):
    return await get_chart(indicator_key=indicator_key, period=period, db=db)
