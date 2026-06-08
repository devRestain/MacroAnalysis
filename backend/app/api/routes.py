"""FastAPI routes — all API endpoints."""
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..core.database import get_db
from ..core.cache import cache_get, cache_set
from ..models.indicators import (
    ChangeSnapshot, NewsItem, DailyInsight, FomcEvent, FedWatch,
    SentimentSignal, Expectation, DivergenceEvent, DivergenceReport,
)
from ..services.daily_insight_service import (
    daily_insight_to_summary_response,
    ensure_daily_insight,
    get_existing_daily_insight,
    get_today_kst,
)
from ..services.observation_query_service import (
    adapt_history_to_chart_response,
    get_dashboard_observation_payload,
    get_observation_history,
)
from ..workers.ai_worker import chat_with_context
from ..workers.celery_app import celery
from ..core.config import settings

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


# ─── /api/summary ────────────────────────────────────────────────────────────

@router.get("/summary")
async def get_summary(db: Session = Depends(get_db)):
    """Home dashboard — all critical data in one shot."""
    cached = await cache_get("summary:v1")
    if cached:
        if cached.get("ai_as_of_date") != get_today_kst().isoformat():
            _enqueue_daily_insight_if_missing()
        return cached

    today = datetime.now()
    today_start = today.replace(hour=0, minute=0, second=0, microsecond=0)

    # Snapshots
    snaps = db.query(ChangeSnapshot).filter(
        ChangeSnapshot.snapshot_date >= today_start - timedelta(days=2)
    ).order_by(desc(ChangeSnapshot.snapshot_date)).all()

    snap_map = {}
    for s in snaps:
        if s.indicator_key not in snap_map:
            snap_map[s.indicator_key] = s

    # Top signals (red or high z-score)
    alerts = [
        _snap_to_dict(s) for s in snap_map.values()
        if s.signal == "red" or (s.z_score_1y and abs(s.z_score_1y) >= 1.5)
    ]
    alerts.sort(key=lambda x: abs(x.get("z_score_1y") or 0), reverse=True)

    # FOMC
    next_fomc = db.query(FomcEvent).filter(
        FomcEvent.meeting_date >= today
    ).order_by(FomcEvent.meeting_date).first()
    latest_fw = None
    if next_fomc:
        latest_fw = db.query(FedWatch).filter(
            FedWatch.meeting_date == next_fomc.meeting_date
        ).order_by(desc(FedWatch.date)).first()

    today_kst = get_today_kst()
    ai_today = get_existing_daily_insight(db, today_kst)
    ai_sum = (
        ai_today
        if ai_today and ai_today.status == "success"
        else db.query(DailyInsight).filter(DailyInsight.status == "success").order_by(desc(DailyInsight.as_of_date)).first()
    )
    if ai_today is None or ai_today.status != "success":
        _enqueue_daily_insight_if_missing()

    # Recent news (top 5)
    news = db.query(NewsItem).order_by(desc(NewsItem.published_at)).limit(5).all()

    dashboard_payload = get_dashboard_observation_payload(db)

    result = {
        "updated_at": today.isoformat(),
        "alerts": alerts[:6],
        "snapshots": {k: _snap_to_dict(v) for k, v in snap_map.items()},
        "equities": dashboard_payload["equities"],
        "yield_curve": dashboard_payload["yield_curve"],
        "fomc": {
            "next_date": str(next_fomc.meeting_date) if next_fomc else None,
            "days_left": (next_fomc.meeting_date - today).days if next_fomc else None,
            "prob_hold": latest_fw.prob_hold if latest_fw else None,
            "prob_cut": latest_fw.prob_cut if latest_fw else None,
            "prob_hike": latest_fw.prob_hike if latest_fw else None,
            "prob_method": "fed_funds_futures_estimate" if latest_fw else None,
        },
        "ai_headline": _daily_insight_headline(ai_sum) if ai_sum else None,
        "ai_as_of_date": ai_sum.as_of_date.isoformat() if ai_sum else None,
        "news_preview": [_news_to_dict(n) for n in news],
    }

    await cache_set("summary:v1", result, ttl=3600)
    return result


# ─── /api/changes ────────────────────────────────────────────────────────────

@router.get("/changes")
async def get_changes(
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    q = db.query(ChangeSnapshot).filter(
        ChangeSnapshot.snapshot_date >= today_start - timedelta(days=2)
    ).order_by(desc(ChangeSnapshot.snapshot_date))
    if category:
        q = q.filter(ChangeSnapshot.category == category)

    seen = {}
    for s in q.all():
        if s.indicator_key not in seen:
            seen[s.indicator_key] = s

    return {"changes": [_snap_to_dict(s) for s in seen.values()]}


# ─── /api/chart/{key} ────────────────────────────────────────────────────────

@router.get("/chart/{indicator_key}")
async def get_chart(
    indicator_key: str,
    period: str = Query("3m", regex="^(1w|1m|3m|1y|all)$"),
    db: Session = Depends(get_db)
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


# ─── /api/news ───────────────────────────────────────────────────────────────

@router.get("/news")
async def get_news(
    category: Optional[str] = None,
    limit: int = Query(30, le=100),
    db: Session = Depends(get_db)
):
    q = db.query(NewsItem).order_by(desc(NewsItem.published_at))
    if category and category != "all":
        q = q.filter(NewsItem.category == category)
    items = q.limit(limit).all()
    return {"news": [_news_to_dict(n) for n in items]}


# ─── /api/sectors ────────────────────────────────────────────────────────────

@router.get("/sectors")
async def get_sectors(db: Session = Depends(get_db)):
    dashboard_payload = get_dashboard_observation_payload(db)
    return {"sectors": dashboard_payload["sectors"]}


# ─── /api/fomc ───────────────────────────────────────────────────────────────

@router.get("/fomc")
async def get_fomc(db: Session = Depends(get_db)):
    events = db.query(FomcEvent).order_by(FomcEvent.meeting_date).all()
    fw = db.query(FedWatch).order_by(desc(FedWatch.date)).first()
    return {
        "meetings": [
            {
                "date": str(e.meeting_date),
                "rate": e.decision_rate,
                "change_bp": e.change_bp,
            }
            for e in events
        ],
        "fedwatch": {
            "prob_hold": fw.prob_hold if fw else None,
            "prob_cut": fw.prob_cut if fw else None,
            "prob_hike": fw.prob_hike if fw else None,
            "prob_method": "fed_funds_futures_estimate",
        } if fw else None,
    }


# ─── /api/ai/summary ─────────────────────────────────────────────────────────

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
        _enqueue_daily_insight_if_missing()
        return daily_insight_to_summary_response(latest_success)

    _enqueue_daily_insight_if_missing()
    ai = get_existing_daily_insight(db, today_kst)
    if not ai:
        raise HTTPException(status_code=404, detail="No AI summary available yet")
    return daily_insight_to_summary_response(ai)


@router.post("/ai/summary/ensure")
async def ensure_ai_summary(
    force: bool = Query(False),
    as_of_date: Optional[str] = None,
    db: Session = Depends(get_db),
):
    try:
        result = ensure_daily_insight(db, as_of_date=as_of_date, force=force)
    except Exception as exc:
        logger.error("Daily insight ensure failed: %s", exc)
        raise HTTPException(status_code=500, detail="Daily insight ensure failed")

    if isinstance(result, dict):
        return result
    return daily_insight_to_summary_response(result)


# ─── /api/ai/chat ────────────────────────────────────────────────────────────

@router.post("/ai/chat")
async def ai_chat(payload: dict, db: Session = Depends(get_db)):
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="AI service not configured")
    message = payload.get("message", "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")
    try:
        reply = chat_with_context(db, message)
        return {"reply": reply}
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="AI chat failed")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _snap_to_dict(s: ChangeSnapshot) -> dict:
    return {
        "key": s.indicator_key,
        "label": s.label,
        "category": s.category,
        "value": s.current_value,
        "unit": s.unit,
        "delta_1d": s.delta_1d,
        "delta_1d_pct": s.delta_1d_pct,
        "delta_1w_pct": s.delta_1w_pct,
        "delta_1m_pct": s.delta_1m_pct,
        "delta_3m_pct": s.delta_3m_pct,
        "z_score_1y": s.z_score_1y,
        "direction": s.direction,
        "signal": s.signal,
        "date": str(s.snapshot_date),
    }


def _news_to_dict(n: NewsItem) -> dict:
    return {
        "id": n.id,
        "source": n.source,
        "title": n.title,
        "summary": n.summary,
        "url": n.url,
        "category": n.category,
        "published_at": str(n.published_at) if n.published_at else None,
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


# ─── /api/divergence ──────────────────────────────────────────────────────────

@router.get("/divergence")
async def get_divergence(
    days: int = Query(7, ge=1, le=90),
    severity: Optional[str] = Query(None, regex="^(WARNING|ALERT)$"),
    db: Session = Depends(get_db),
):
    """최근 divergence 이벤트 목록 + 연결된 리포트."""
    cutoff = datetime.now() - timedelta(days=days)
    q = db.query(DivergenceEvent).filter(DivergenceEvent.batch_date >= cutoff)
    if severity:
        q = q.filter(DivergenceEvent.severity == severity)
    events = q.order_by(desc(DivergenceEvent.batch_date)).limit(50).all()

    result = []
    for ev in events:
        report = (
            db.query(DivergenceReport)
            .filter(DivergenceReport.event_id == ev.id)
            .first()
        )
        result.append({
            "id": ev.id,
            "batch_date": str(ev.batch_date),
            "actor": ev.actor,
            "dimension": ev.dimension,
            "raw_score": ev.raw_score,
            "consensus_score": ev.consensus_score,
            "adjusted_gap": ev.adjusted_gap,
            "severity": ev.severity,
            "inertia_reset": ev.inertia_reset,
            "momentum_sign_change": ev.momentum_sign_change,
            "multiplier_applied": ev.multiplier_applied,
            "report": {
                "headline": report.headline,
                "background": report.background,
                "action_plan": report.action_plan,
                "risk_scenario": report.risk_scenario,
            } if report else None,
        })
    return {"divergence_events": result, "count": len(result)}


# ─── /api/expectations ────────────────────────────────────────────────────────

@router.get("/expectations")
async def get_expectations(
    actor: Optional[str] = None,
    dimension: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Expectation 시계열 (관성 모델 컨센서스 추이)."""
    cutoff = datetime.now() - timedelta(days=days)
    q = db.query(Expectation).filter(Expectation.date >= cutoff)
    if actor:
        q = q.filter(Expectation.actor == actor)
    if dimension:
        q = q.filter(Expectation.dimension == dimension)
    rows = q.order_by(Expectation.actor, Expectation.dimension, Expectation.date).all()

    # actor×dimension 별로 그룹화
    from collections import defaultdict
    groups: dict = defaultdict(list)
    for r in rows:
        groups[f"{r.actor}/{r.dimension}"].append({
            "date": str(r.date),
            "consensus_score": r.consensus_score,
            "raw_score": r.raw_score,
            "consensus_strength": r.consensus_strength,
            "inertia_coefficient": r.inertia_coefficient,
            "inertia_reset": r.inertia_reset,
            "momentum_score": r.momentum_score,
        })

    return {"expectations": dict(groups)}


# ─── /api/sentiment/signals ───────────────────────────────────────────────────

@router.get("/sentiment/signals")
async def get_sentiment_signals(
    batch_date: Optional[str] = None,
    actor: Optional[str] = None,
    dimension: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """개별 sentiment 신호 조회."""
    q = db.query(SentimentSignal)
    if batch_date:
        try:
            bd = datetime.fromisoformat(batch_date)
            q = q.filter(
                SentimentSignal.batch_date >= bd,
                SentimentSignal.batch_date < bd + timedelta(days=1),
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="batch_date must be ISO format")
    if actor:
        q = q.filter(SentimentSignal.actor == actor)
    if dimension:
        q = q.filter(SentimentSignal.dimension == dimension)

    signals = q.order_by(desc(SentimentSignal.extracted_at)).limit(limit).all()
    return {
        "signals": [
            {
                "id": s.id,
                "batch_date": str(s.batch_date),
                "source_type": s.source_type,
                "source_id": s.source_id,
                "actor": s.actor,
                "dimension": s.dimension,
                "stance": s.stance,
                "stance_score": s.stance_score,
                "intensity": s.intensity,
                "confidence": s.confidence,
                "evidence": s.evidence,
            }
            for s in signals
        ],
        "count": len(signals),
    }
