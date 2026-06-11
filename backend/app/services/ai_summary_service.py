from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..core.config import settings
from ..models import AiSummary, CommunicationEvent, EconomicCalendarEvent
from .observation_query_service import get_ai_context_payload

SUMMARY_TYPES = {"macro", "market", "calendar", "communication"}


def get_latest_ai_summary(
    db: Session,
    *,
    summary_type: str = "macro",
    target_key: str | None = None,
    days: int | None = None,
) -> AiSummary | None:
    query = db.query(AiSummary).filter(AiSummary.summary_type == summary_type)
    if target_key is None:
        query = query.filter(AiSummary.target_key.is_(None))
    else:
        query = query.filter(AiSummary.target_key == target_key)
    if days is not None:
        cutoff = _utcnow_naive() - timedelta(days=days)
        query = query.filter(AiSummary.summary_date >= cutoff)
    return query.order_by(desc(AiSummary.summary_date), desc(AiSummary.id)).first()


def ensure_ai_summary(
    db: Session,
    *,
    summary_type: str = "macro",
    target_key: str | None = None,
    days: int = 7,
    force: bool = False,
) -> AiSummary:
    normalized_type = summary_type.lower()
    if normalized_type not in SUMMARY_TYPES:
        raise ValueError(f"Unsupported summary_type: {summary_type}")

    if not force:
        existing = get_latest_ai_summary(db, summary_type=normalized_type, target_key=target_key, days=days)
        if existing is not None:
            return existing

    context = _build_summary_context(db, summary_type=normalized_type, target_key=target_key, days=days)
    payload = _generate_summary_payload(summary_type=normalized_type, target_key=target_key, context=context)
    row = AiSummary(
        summary_date=_utcnow_naive(),
        summary_type=normalized_type,
        target_key=target_key,
        headline=payload["headline"],
        body=payload["body"],
        indicators_snapshot=_json_safe(payload.get("indicators_snapshot")),
        model_used=payload["model_used"],
        metadata_json=_json_safe(payload.get("metadata_json")),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def ai_summary_to_dict(row: AiSummary) -> dict[str, Any]:
    return {
        "id": row.id,
        "summary_date": row.summary_date.isoformat(),
        "summary_type": row.summary_type,
        "target_key": row.target_key,
        "headline": row.headline,
        "body": row.body,
        "model_used": row.model_used,
        "metadata": row.metadata_json or {},
    }


def _build_summary_context(
    db: Session,
    *,
    summary_type: str,
    target_key: str | None,
    days: int,
) -> dict[str, Any]:
    if summary_type in {"macro", "market"}:
        payload = get_ai_context_payload(db, None)
        if summary_type == "market":
            filtered = [
                item
                for item in payload["series"]
                if item["series_key"] in {"^GSPC", "^IXIC", "^VIX", "DX-Y.NYB", "CL=F", "GC=F", "HG=F", "DGS2", "DGS10"}
            ]
        else:
            filtered = payload["series"]
        lines = [
            (
                f"- {item['name'] or item['series_key']} ({item['series_key']}): {item['latest_value']}"
                f"{item.get('unit') or ''} / latest={item.get('latest_date')}"
            )
            for item in filtered
            if item.get("latest_value") is not None
        ]
        return {
            "summary_type": summary_type,
            "target_key": target_key,
            "context_text": "\n".join(lines) if lines else "No market observations available.",
            "indicators_snapshot": filtered,
            "metadata_json": {"series_count": len(filtered)},
        }

    if summary_type == "calendar":
        cutoff = _utcnow_naive()
        end = cutoff + timedelta(days=days)
        events = (
            db.query(EconomicCalendarEvent)
            .filter(EconomicCalendarEvent.event_date >= cutoff, EconomicCalendarEvent.event_date <= end)
            .order_by(EconomicCalendarEvent.event_date)
            .all()
        )
        if target_key:
            events = [event for event in events if target_key.lower() in event.title.lower()]
        lines = [f"- {event.event_date.isoformat()} | {event.title} | {event.category}" for event in events[:15]]
        return {
            "summary_type": summary_type,
            "target_key": target_key,
            "context_text": "\n".join(lines) if lines else "No upcoming calendar events available.",
            "indicators_snapshot": None,
            "metadata_json": {"event_count": len(events)},
        }

    communication_query = db.query(CommunicationEvent)
    if target_key:
        communication_query = communication_query.filter(CommunicationEvent.title.ilike(f"%{target_key}%"))
    communications = (
        communication_query.order_by(desc(CommunicationEvent.event_date), desc(CommunicationEvent.id)).limit(max(days, 5)).all()
    )
    lines = [
        f"- {event.event_date.isoformat()} | {event.event_type} | {event.title}\n{(event.content_text or '')[:400]}"
        for event in communications
    ]
    return {
        "summary_type": summary_type,
        "target_key": target_key,
        "context_text": "\n".join(lines) if lines else "No communication events available.",
        "indicators_snapshot": None,
        "metadata_json": {"event_count": len(communications)},
    }


def _generate_summary_payload(*, summary_type: str, target_key: str | None, context: dict[str, Any]) -> dict[str, Any]:
    fallback = _fallback_summary_payload(summary_type=summary_type, target_key=target_key, context=context)
    if not settings.OPENAI_API_KEY:
        return fallback

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=settings.AI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You summarize macro and central-bank information in Korean. "
                        "Return JSON with headline and body."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"summary_type={summary_type}\n"
                        f"target_key={target_key or 'all'}\n"
                        f"context:\n{context['context_text']}\n"
                        'Return JSON like {"headline":"...", "body":"..."}'
                    ),
                },
            ],
            temperature=0.3,
            max_tokens=600,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)
        return {
            "headline": parsed.get("headline") or fallback["headline"],
            "body": parsed.get("body") or fallback["body"],
            "indicators_snapshot": context.get("indicators_snapshot"),
            "metadata_json": context.get("metadata_json"),
            "model_used": settings.AI_MODEL,
        }
    except Exception:
        return fallback


def _fallback_summary_payload(*, summary_type: str, target_key: str | None, context: dict[str, Any]) -> dict[str, Any]:
    target_label = target_key or "all"
    return {
        "headline": f"{summary_type.capitalize()} summary ({target_label})",
        "body": context["context_text"] or f"No context available for {summary_type} summary.",
        "indicators_snapshot": context.get("indicators_snapshot"),
        "metadata_json": context.get("metadata_json"),
        "model_used": settings.AI_MODEL,
    }


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str)) if value is not None else None


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
