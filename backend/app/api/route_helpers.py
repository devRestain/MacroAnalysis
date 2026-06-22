from __future__ import annotations

import logging
from datetime import timezone

from ..models import ChangeSnapshot, DailyInsight, EconomicCalendarEvent, NewsItem
from ..core.config import settings
from ..services.localization import localize_calendar_event_dict, localize_snapshot_dict

logger = logging.getLogger(__name__)


def snap_to_dict(snapshot: ChangeSnapshot, *, locale: str = "ko") -> dict:
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


def calendar_event_to_dict(event: EconomicCalendarEvent, *, include_details: bool, locale: str = "ko") -> dict:
    event_dt = event.event_datetime_utc or event.event_date
    if event_dt.tzinfo is None:
        event_utc = event_dt.replace(tzinfo=timezone.utc).isoformat()
    else:
        event_utc = event_dt.astimezone(timezone.utc).isoformat()

    related_indicator_keys = event.related_indicator_keys
    if related_indicator_keys is None and event.related_indicator_key:
        related_indicator_keys = [event.related_indicator_key]

    payload = {
        "id": event.id,
        "event_date": event.event_date,
        "event_end_date": event.event_end_date,
        "event_time": event.event_time,
        "timezone": event.timezone,
        "event_datetime_utc": event.event_datetime_utc or event.event_date,
        "event_date_local": event.event_date_local or event.event_date.date(),
        "event_time_local": event.event_time_local or event.event_time,
        "display_time": _build_display_time(event.event_time_local or event.event_time, event.timezone),
        "event_key": event.event_key,
        "event_type": event.event_type,
        "category": event.category,
        "title": event.title,
        "display_name": event.display_name or event.title,
        "short_name": event.short_name or event.display_name or event.title,
        "country": event.country,
        "source": event.source,
        "source_url": event.source_url,
        "importance": event.importance,
        "status": event.status,
        "date_precision": event.date_precision or ("datetime_estimated" if (event.event_time_local or event.event_time) else "date_only"),
        "time_source": event.time_source,
        "time_confidence": event.time_confidence,
        "beginner_description": event.beginner_description,
        "why_it_matters": event.why_it_matters,
        "watch_items": event.watch_items,
        "related_indicator_key": event.related_indicator_key,
        "related_indicator_keys": related_indicator_keys,
        "related_asset": event.related_asset,
        "actual_value": event.actual_value,
        "forecast_value": event.forecast_value,
        "previous_value": event.previous_value,
        "unit": event.unit,
        "metadata": {
            **(event.metadata_json or {}),
            "event_local_date": (event.event_date_local or event.event_date.date()).isoformat(),
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
    return localize_calendar_event_dict(payload, locale=locale)


def _build_display_time(local_time: str | None, timezone_name: str | None) -> str | None:
    if not local_time:
        return None
    tz_label = "ET" if timezone_name == "America/New_York" else timezone_name
    return f"{local_time} {tz_label}".strip()
