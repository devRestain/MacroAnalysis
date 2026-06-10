from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...models import DivergenceEvent, DivergenceReport, Expectation, SentimentSignal
from ..sentiment_schemas import SentimentSignalListResponse

router = APIRouter(prefix="/api")


@router.get("/divergence")
async def get_divergence(
    days: int = Query(7, ge=1, le=90),
    severity: str | None = Query(None, regex="^(WARNING|ALERT)$"),
    db: Session = Depends(get_db),
):
    cutoff = datetime.now() - timedelta(days=days)
    query = db.query(DivergenceEvent).filter(DivergenceEvent.batch_date >= cutoff)
    if severity:
        query = query.filter(DivergenceEvent.severity == severity)
    events = query.order_by(desc(DivergenceEvent.batch_date)).limit(50).all()

    result = []
    for event in events:
        report = db.query(DivergenceReport).filter(DivergenceReport.event_id == event.id).first()
        result.append(
            {
                "id": event.id,
                "batch_date": str(event.batch_date),
                "actor": event.actor,
                "dimension": event.dimension,
                "raw_score": event.raw_score,
                "consensus_score": event.consensus_score,
                "adjusted_gap": event.adjusted_gap,
                "severity": event.severity,
                "inertia_reset": event.inertia_reset,
                "momentum_sign_change": event.momentum_sign_change,
                "multiplier_applied": event.multiplier_applied,
                "report": {
                    "headline": report.headline,
                    "background": report.background,
                    "action_plan": report.action_plan,
                    "risk_scenario": report.risk_scenario,
                }
                if report
                else None,
            }
        )
    return {"divergence_events": result, "count": len(result)}


@router.get("/expectations")
async def get_expectations(
    actor: str | None = None,
    dimension: str | None = None,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    cutoff = datetime.now() - timedelta(days=days)
    query = db.query(Expectation).filter(Expectation.date >= cutoff)
    if actor:
        query = query.filter(Expectation.actor == actor)
    if dimension:
        query = query.filter(Expectation.dimension == dimension)
    rows = query.order_by(Expectation.actor, Expectation.dimension, Expectation.date).all()

    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[f"{row.actor}/{row.dimension}"].append(
            {
                "date": str(row.date),
                "consensus_score": row.consensus_score,
                "raw_score": row.raw_score,
                "consensus_strength": row.consensus_strength,
                "inertia_coefficient": row.inertia_coefficient,
                "inertia_reset": row.inertia_reset,
                "momentum_score": row.momentum_score,
            }
        )

    return {"expectations": dict(groups)}


@router.get("/sentiment/signals", response_model=SentimentSignalListResponse)
async def get_sentiment_signals(
    batch_date: str | None = None,
    actor: str | None = None,
    dimension: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(SentimentSignal)
    if batch_date:
        try:
            parsed_date = datetime.fromisoformat(batch_date)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="batch_date must be ISO format") from exc
        query = query.filter(
            SentimentSignal.batch_date >= parsed_date,
            SentimentSignal.batch_date < parsed_date + timedelta(days=1),
        )
    if actor:
        query = query.filter(SentimentSignal.actor == actor)
    if dimension:
        query = query.filter(SentimentSignal.dimension == dimension)

    signals = query.order_by(desc(SentimentSignal.extracted_at)).limit(limit).all()
    return {
        "signals": [
            {
                "id": signal.id,
                "batch_date": str(signal.batch_date),
                "source_type": signal.source_type,
                "source_id": signal.source_id,
                "actor": signal.actor,
                "dimension": signal.dimension,
                "stance": signal.stance,
                "stance_score": signal.stance_score,
                "intensity": signal.intensity,
                "confidence": signal.confidence,
                "evidence": signal.evidence,
            }
            for signal in signals
        ],
        "count": len(signals),
    }
