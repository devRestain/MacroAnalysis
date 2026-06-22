from __future__ import annotations

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ...core.cache import cache_get, cache_set
from ...core.config import settings
from ...core.database import get_db
from ...models import ChangeSnapshot, DailyInsight, NewsItem
from ...services.calendar_query_service import get_latest_fedwatch_for_meeting, get_next_fomc_meeting_date
from ...services.localization import label_for, localize_snapshot_dict, normalize_locale
from ...services.daily_insight_service import get_existing_daily_insight, get_today_kst
from ...services.observation_query_service import get_dashboard_observation_payload
from ...workers.celery_app import celery

router = APIRouter(prefix="/api")
SUMMARY_CACHE_PREFIX = "summary:v2"
logger = logging.getLogger(__name__)


@router.get("/summary")
async def get_summary(lang: str | None = Query(None), db: Session = Depends(get_db)):
    locale = normalize_locale(lang)
    cached = await cache_get(f"{SUMMARY_CACHE_PREFIX}:{locale}")
    if cached:
        if cached.get("ai_as_of_date") != get_today_kst().isoformat():
            _enqueue_daily_insight_if_missing()
        return cached

    today = datetime.now()
    today_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
    snapshots = _latest_snapshots(db, since=today_start - timedelta(days=2))

    snapshot_map: dict[str, ChangeSnapshot] = {}
    for snapshot in snapshots:
        if snapshot.indicator_key not in snapshot_map:
            snapshot_map[snapshot.indicator_key] = snapshot

    alerts = [
        _snapshot_to_dict(snapshot, locale=locale)
        for snapshot in snapshot_map.values()
        if snapshot.signal == "red" or (snapshot.z_score_1y and abs(snapshot.z_score_1y) >= 1.5)
    ]
    alerts.sort(key=lambda item: abs(item.get("z_score_1y") or 0), reverse=True)

    next_fomc_date = get_next_fomc_meeting_date(db, now=today)
    latest_fw = get_latest_fedwatch_for_meeting(db, next_fomc_date)

    today_kst = get_today_kst()
    ai_today = get_existing_daily_insight(db, today_kst)
    ai_summary = (
        ai_today
        if ai_today and ai_today.status == "success"
        else db.query(DailyInsight).filter(DailyInsight.status == "success").order_by(desc(DailyInsight.as_of_date)).first()
    )
    if ai_today is None or ai_today.status != "success":
        _enqueue_daily_insight_if_missing()

    news = db.query(NewsItem).order_by(desc(NewsItem.published_at)).limit(5).all()
    dashboard_payload = get_dashboard_observation_payload(db)
    latest_snapshot_at = max((snapshot.snapshot_date for snapshot in snapshot_map.values()), default=None)

    result = {
        "updated_at": (latest_snapshot_at or today).isoformat(),
        "alerts": alerts[:6],
        "snapshots": {key: _snapshot_to_dict(value, locale=locale) for key, value in snapshot_map.items()},
        "equities": dashboard_payload["equities"],
        "yield_curve": dashboard_payload["yield_curve"],
        "fomc": {
            "next_date": str(next_fomc_date) if next_fomc_date else None,
            "days_left": (next_fomc_date - today).days if next_fomc_date else None,
            "prob_hold": latest_fw.prob_hold if latest_fw else None,
            "prob_cut": latest_fw.prob_cut if latest_fw else None,
            "prob_hike": latest_fw.prob_hike if latest_fw else None,
            "prob_method": "fed_funds_futures_estimate" if latest_fw else None,
            "prob_method_label": label_for("prob_method", "fed_funds_futures_estimate", locale=locale, fallback="fed_funds_futures_estimate") if latest_fw else None,
        },
        "ai_headline": _daily_insight_headline(ai_summary) if ai_summary else None,
        "ai_as_of_date": ai_summary.as_of_date.isoformat() if ai_summary else None,
        "news_preview": [_news_to_dict(item) for item in news],
    }
    await cache_set(f"{SUMMARY_CACHE_PREFIX}:{locale}", result, ttl=3600)
    return result


@router.get("/changes")
async def get_changes(category: str | None = None, lang: str | None = Query(None), db: Session = Depends(get_db)):
    locale = normalize_locale(lang)
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    snapshots = _latest_snapshots(db, since=today_start - timedelta(days=2), category=category)
    seen: dict[str, ChangeSnapshot] = {}
    for snapshot in snapshots:
        if snapshot.indicator_key not in seen:
            seen[snapshot.indicator_key] = snapshot
    return {"changes": [_snapshot_to_dict(snapshot, locale=locale) for snapshot in seen.values()]}


@router.get("/sectors")
async def get_sectors(db: Session = Depends(get_db)):
    dashboard_payload = get_dashboard_observation_payload(db)
    return {"sectors": dashboard_payload["sectors"]}


def _latest_snapshots(
    db: Session,
    *,
    since: datetime,
    category: str | None = None,
) -> list[ChangeSnapshot]:
    query = db.query(ChangeSnapshot)
    if category:
        query = query.filter(ChangeSnapshot.category == category)

    recent = (
        query
        .filter(ChangeSnapshot.snapshot_date >= since)
        .order_by(desc(ChangeSnapshot.snapshot_date))
        .all()
    )
    if recent:
        return recent

    return query.order_by(desc(ChangeSnapshot.snapshot_date)).all()


def _snapshot_to_dict(snapshot: ChangeSnapshot, *, locale: str = "ko") -> dict:
    payload = {
        "key": snapshot.indicator_key,
        "label": snapshot.label,
        "category": snapshot.category,
        "value": snapshot.current_value,
        "unit": snapshot.unit,
        "delta_1d": snapshot.delta_1d,
        "delta_1d_pct": snapshot.delta_1d_pct,
        "delta_1w_pct": snapshot.delta_1w_pct,
        "delta_1m_pct": snapshot.delta_1m_pct,
        "delta_3m_pct": snapshot.delta_3m_pct,
        "z_score_1y": snapshot.z_score_1y,
        "direction": snapshot.direction,
        "signal": snapshot.signal,
        "date": str(snapshot.snapshot_date),
    }
    return localize_snapshot_dict(payload, locale=locale)


def _news_to_dict(item: NewsItem) -> dict:
    return {
        "id": item.id,
        "source": item.source,
        "title": item.title,
        "summary": item.summary,
        "url": item.url,
        "category": item.category,
        "published_at": str(item.published_at) if item.published_at else None,
    }


def _daily_insight_headline(insight: DailyInsight | None) -> str | None:
    if not insight or not insight.summary:
        return None
    return insight.summary.splitlines()[0].strip()[:200]


def _enqueue_daily_insight_if_missing() -> None:
    if not settings.AI_DAILY_INSIGHT_ENABLED or not settings.AI_DAILY_INSIGHT_BACKFILL_TRIGGER_ENABLED:
        return
    try:
        celery.send_task("app.workers.celery_app.task_ensure_daily_insight")
    except Exception as exc:
        logger.warning("Failed to enqueue daily insight ensure task: %s", exc)
