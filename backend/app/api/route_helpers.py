from __future__ import annotations

import logging
from datetime import timezone

from ..models import ChangeSnapshot, DailyInsight, EconomicCalendarEvent, NewsItem
from ..core.config import settings

logger = logging.getLogger(__name__)


def snap_to_dict(snapshot: ChangeSnapshot) -> dict:
    return {
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


def news_to_dict(item: NewsItem) -> dict:
    return {
        "id": item.id,
        "source": item.source,
        "title": item.title,
        "summary": item.summary,
        "url": item.url,
        "category": item.category,
        "published_at": str(item.published_at) if item.published_at else None,
    }


def daily_insight_headline(insight: DailyInsight | None) -> str | None:
    if not insight or not insight.summary:
        return None
    return insight.summary.splitlines()[0].strip()[:200]


def enqueue_daily_insight_if_missing() -> None:
    if not settings.AI_DAILY_INSIGHT_ENABLED or not settings.AI_DAILY_INSIGHT_BACKFILL_TRIGGER_ENABLED:
        return
    try:
        from ..workers.celery_app import celery

        celery.send_task("app.workers.celery_app.task_ensure_daily_insight")
    except Exception as exc:
        logger.warning("Failed to enqueue daily insight ensure task: %s", exc)


def calendar_event_to_dict(event: EconomicCalendarEvent, *, include_details: bool) -> dict:
    if event.event_date.tzinfo is None:
        event_utc = event.event_date.replace(tzinfo=timezone.utc).isoformat()
    else:
        event_utc = event.event_date.astimezone(timezone.utc).isoformat()

    payload = {
        "id": event.id,
        "event_date": event.event_date,
        "event_end_date": event.event_end_date,
        "event_time": event.event_time,
        "timezone": event.timezone,
        "event_key": event.event_key,
        "event_type": event.event_type,
        "category": event.category,
        "title": event.title,
        "country": event.country,
        "source": event.source,
        "source_url": event.source_url,
        "importance": event.importance,
        "status": event.status,
        "related_indicator_key": event.related_indicator_key,
        "related_asset": event.related_asset,
        "actual_value": event.actual_value,
        "forecast_value": event.forecast_value,
        "previous_value": event.previous_value,
        "unit": event.unit,
        "metadata": {
            **(event.metadata_json or {}),
            "event_local_date": event.event_date.date().isoformat(),
            "event_utc": event_utc,
        },
        "details": None,
    }
    if include_details and event.fomc_detail is not None:
        payload["details"] = {
            "fomc": {
                "meeting_start_date": event.fomc_detail.meeting_start_date.isoformat() if event.fomc_detail.meeting_start_date else None,
                "meeting_end_date": event.fomc_detail.meeting_end_date.isoformat(),
                "decision_rate": event.fomc_detail.decision_rate,
                "target_rate_lower": event.fomc_detail.target_rate_lower,
                "target_rate_upper": event.fomc_detail.target_rate_upper,
                "change_bp": event.fomc_detail.change_bp,
                "statement_url": event.fomc_detail.statement_url,
                "minutes_url": event.fomc_detail.minutes_url,
                "implementation_note_url": event.fomc_detail.implementation_note_url,
                "press_conference_url": event.fomc_detail.press_conference_url,
                "projection_materials_url": event.fomc_detail.projection_materials_url,
                "has_sep": event.fomc_detail.has_sep,
            }
        }
    return payload
