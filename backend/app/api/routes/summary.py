from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ...core.cache import cache_get, cache_set
from ...core.database import get_db
from ...models import ChangeSnapshot, DailyInsight, NewsItem
from ...services.calendar_query_service import get_latest_fedwatch_for_meeting, get_next_fomc_meeting_date
from ...services.daily_insight_service import get_existing_daily_insight, get_today_kst
from ...services.observation_query_service import get_dashboard_observation_payload
from ..route_helpers import daily_insight_headline, enqueue_daily_insight_if_missing, news_to_dict, snap_to_dict

router = APIRouter(prefix="/api")


@router.get("/summary")
async def get_summary(db: Session = Depends(get_db)):
    cached = await cache_get("summary:v1")
    if cached:
        if cached.get("ai_as_of_date") != get_today_kst().isoformat():
            enqueue_daily_insight_if_missing()
        return cached

    today = datetime.now()
    today_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
    snapshots = (
        db.query(ChangeSnapshot)
        .filter(ChangeSnapshot.snapshot_date >= today_start - timedelta(days=2))
        .order_by(desc(ChangeSnapshot.snapshot_date))
        .all()
    )

    snapshot_map: dict[str, ChangeSnapshot] = {}
    for snapshot in snapshots:
        if snapshot.indicator_key not in snapshot_map:
            snapshot_map[snapshot.indicator_key] = snapshot

    alerts = [
        snap_to_dict(snapshot)
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
        enqueue_daily_insight_if_missing()

    news = db.query(NewsItem).order_by(desc(NewsItem.published_at)).limit(5).all()
    dashboard_payload = get_dashboard_observation_payload(db)

    result = {
        "updated_at": today.isoformat(),
        "alerts": alerts[:6],
        "snapshots": {key: snap_to_dict(value) for key, value in snapshot_map.items()},
        "equities": dashboard_payload["equities"],
        "yield_curve": dashboard_payload["yield_curve"],
        "fomc": {
            "next_date": str(next_fomc_date) if next_fomc_date else None,
            "days_left": (next_fomc_date - today).days if next_fomc_date else None,
            "prob_hold": latest_fw.prob_hold if latest_fw else None,
            "prob_cut": latest_fw.prob_cut if latest_fw else None,
            "prob_hike": latest_fw.prob_hike if latest_fw else None,
            "prob_method": "fed_funds_futures_estimate" if latest_fw else None,
        },
        "ai_headline": daily_insight_headline(ai_summary) if ai_summary else None,
        "ai_as_of_date": ai_summary.as_of_date.isoformat() if ai_summary else None,
        "news_preview": [news_to_dict(item) for item in news],
    }
    await cache_set("summary:v1", result, ttl=3600)
    return result


@router.get("/changes")
async def get_changes(category: str | None = None, db: Session = Depends(get_db)):
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    query = (
        db.query(ChangeSnapshot)
        .filter(ChangeSnapshot.snapshot_date >= today_start - timedelta(days=2))
        .order_by(desc(ChangeSnapshot.snapshot_date))
    )
    if category:
        query = query.filter(ChangeSnapshot.category == category)

    seen: dict[str, ChangeSnapshot] = {}
    for snapshot in query.all():
        if snapshot.indicator_key not in seen:
            seen[snapshot.indicator_key] = snapshot
    return {"changes": [snap_to_dict(snapshot) for snapshot in seen.values()]}


@router.get("/sectors")
async def get_sectors(db: Session = Depends(get_db)):
    dashboard_payload = get_dashboard_observation_payload(db)
    return {"sectors": dashboard_payload["sectors"]}
