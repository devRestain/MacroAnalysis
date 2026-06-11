from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy.orm import Session

from ..collectors.communication_collector import collect_fed_communications
from ..collectors.fomc_collector import collect_fedwatch, collect_fomc_calendar
from ..collectors.fred_collector import collect_credit_spreads, collect_macro, collect_rates
from ..collectors.fx_collector import collect_exchange_rates
from ..collectors.market_collector import collect_equity_indices, collect_real_economy, collect_sectors
from ..collectors.news_collector import collect_fed_rss, collect_finnhub_news
from ..core.cache import cache_delete_pattern_sync, cache_delete_sync
from ..core.config import settings
from ..collectors.result_utils import add_counts, empty_counts
from .calendar_collection_service import collect_calendar_events
from .daily_insight_service import get_existing_daily_insight, get_today_kst
from .collection_guard import get_default_min_interval, run_with_guard

logger = logging.getLogger(__name__)

ASIA_EQUITY_TICKERS = ["^KS11", "^N225", "000001.SS"]


def run_morning_batch(db: Session) -> dict[str, Any]:
    if not settings.MORNING_BATCH_ENABLED:
        return _disabled_batch_result("morning")
    jobs = [
        _guarded_job("fred_rates", "fred", lambda session: collect_rates(session)),
        _guarded_job("fred_macro", "fred", lambda session: collect_macro(session)),
        _guarded_job("credit_spreads", "fred", lambda session: collect_credit_spreads(session)),
        _guarded_job(
            "equity_us_global",
            "yfinance",
            lambda session: _collect_us_global_market_bundle(session),
        ),
        _guarded_job("sector_performance", "yfinance", lambda session: collect_sectors(session)),
        _guarded_job("fedwatch", "cme", lambda session: collect_fedwatch(session)),
        _guarded_job("fx_rates", "exchangerate-api", lambda session: collect_exchange_rates(session)),
        _guarded_job("news", "news", lambda session: _collect_news_bundle(session)),
        _guarded_job("snapshot_compute", "internal", lambda session: _compute_snapshots(session)),
        _callable_job("daily_insight_enqueue", lambda session: _enqueue_daily_insight_if_missing(session), invalidate_cache=False)
        if settings.AI_DAILY_INSIGHT_TRIGGER_IN_MORNING_BATCH
        else _maintenance_job("daily_insight_enqueue_disabled"),
    ]
    return _run_batch(db, "morning", jobs)


def run_noon_batch(db: Session) -> dict[str, Any]:
    if not settings.NOON_BATCH_ENABLED:
        return _disabled_batch_result("noon")
    jobs = [
        _guarded_job("news", "news", lambda session: _collect_news_bundle(session)),
        _guarded_job("fx_rates", "exchangerate-api", lambda session: collect_exchange_rates(session)),
        _guarded_job("snapshot_compute", "internal", lambda session: _compute_snapshots(session)),
        _callable_job("daily_insight_enqueue", lambda session: _enqueue_daily_insight_if_missing(session), invalidate_cache=False)
        if settings.AI_DAILY_INSIGHT_BACKFILL_TRIGGER_ENABLED
        else _maintenance_job("daily_insight_enqueue_disabled"),
    ]
    return _run_batch(db, "noon", jobs)


def run_evening_batch(db: Session) -> dict[str, Any]:
    if not settings.EVENING_BATCH_ENABLED:
        return _disabled_batch_result("evening")
    jobs = [
        _guarded_job(
            "equity_asia",
            "yfinance",
            lambda session: collect_equity_indices(session, tickers=ASIA_EQUITY_TICKERS),
        ),
        _guarded_job("fx_rates", "exchangerate-api", lambda session: collect_exchange_rates(session)),
        _guarded_job("news", "news", lambda session: _collect_news_bundle(session)),
        _guarded_job("snapshot_compute", "internal", lambda session: _compute_snapshots(session)),
        _callable_job("daily_insight_enqueue", lambda session: _enqueue_daily_insight_if_missing(session), invalidate_cache=False)
        if settings.AI_DAILY_INSIGHT_BACKFILL_TRIGGER_ENABLED
        else _maintenance_job("daily_insight_enqueue_disabled"),
    ]
    return _run_batch(db, "evening", jobs)


def run_weekly_batch(db: Session) -> dict[str, Any]:
    if not settings.WEEKLY_BATCH_ENABLED:
        return _disabled_batch_result("weekly")
    jobs = [
        _guarded_job("calendar_events", "calendar", lambda session: collect_calendar_events(session)),
        _guarded_job("fomc_calendar", "federalreserve", lambda session: collect_fomc_calendar(session)),
        _guarded_job("fed_communications", "federalreserve", lambda session: collect_fed_communications(session)),
        _maintenance_job("collection_runs_maintenance"),
    ]
    return _run_batch(db, "weekly", jobs)


def run_calendar_batch(db: Session) -> dict[str, Any]:
    jobs = [
        _guarded_job("calendar_events", "calendar", lambda session: collect_calendar_events(session)),
        _guarded_job("fomc_calendar", "federalreserve", lambda session: collect_fomc_calendar(session)),
        _guarded_job("fed_communications", "federalreserve", lambda session: collect_fed_communications(session)),
    ]
    return _run_batch(db, "calendar", jobs)


def run_guarded_job(db: Session, job_key: str) -> dict[str, Any]:
    jobs = {job["job_key"]: job for job in _all_job_definitions()}
    if job_key not in jobs:
        raise ValueError(f"Unknown collection job: {job_key}")
    return _execute_job(db, jobs[job_key])


def _run_batch(db: Session, batch_name: str, jobs: list[dict[str, Any]]) -> dict[str, Any]:
    started_at = _utcnow()
    results = []
    invalidate_cache = False

    for job in jobs:
        result = _execute_job(db, job)
        results.append(result)
        if result["status"] in {"success", "failed"} and job.get("invalidate_cache", False):
            invalidate_cache = True

    if invalidate_cache:
        _invalidate_dashboard_cache()
        _invalidate_calendar_cache()

    return {
        "batch": batch_name,
        "started_at": started_at.isoformat(),
        "finished_at": _utcnow().isoformat(),
        "jobs": results,
    }


def _disabled_batch_result(batch_name: str) -> dict[str, Any]:
    now = _utcnow().isoformat()
    return {
        "batch": batch_name,
        "started_at": now,
        "finished_at": now,
        "jobs": [
            {
                "job_key": f"{batch_name}_batch",
                "status": "skipped",
                "reason": "batch_disabled",
                "fetched_count": 0,
                "inserted_count": 0,
                "updated_count": 0,
            }
        ],
    }


def _execute_job(db: Session, job: dict[str, Any]) -> dict[str, Any]:
    if job["type"] == "guarded":
        result = run_with_guard(
            db,
            job_key=job["job_key"],
            provider=job["provider"],
            min_interval_minutes=job["min_interval_minutes"],
            fn=job["fn"],
        )
    elif job["type"] == "callable":
        try:
            result = job["fn"](db)
        except Exception as exc:
            result = {
                "job_key": job["job_key"],
                "status": "failed",
                "reason": str(exc),
                "fetched_count": 0,
                "inserted_count": 0,
                "updated_count": 0,
            }
    elif job["type"] == "placeholder":
        result = {
            "job_key": job["job_key"],
            "status": "skipped",
            "reason": job["reason"],
            "fetched_count": 0,
            "inserted_count": 0,
            "updated_count": 0,
        }
    else:
        result = {
            "job_key": job["job_key"],
            "status": "success",
            "reason": "maintenance_noop",
            "fetched_count": 0,
            "inserted_count": 0,
            "updated_count": 0,
        }
    return result


def _guarded_job(job_key: str, provider: str, fn: Callable[[Session], Any]) -> dict[str, Any]:
    return {
        "type": "guarded",
        "job_key": job_key,
        "provider": provider,
        "min_interval_minutes": get_default_min_interval(job_key),
        "fn": fn,
        "invalidate_cache": job_key in {"snapshot_compute", "fred_rates", "fred_macro", "credit_spreads", "equity_us_global", "equity_asia", "sector_performance", "fedwatch", "fx_rates", "news", "fomc_calendar", "fed_communications", "calendar_events"},
    }


def _placeholder_job(job_key: str, reason: str) -> dict[str, Any]:
    return {
        "type": "placeholder",
        "job_key": job_key,
        "reason": reason,
        "invalidate_cache": False,
    }


def _callable_job(job_key: str, fn: Callable[[Session], Any], *, invalidate_cache: bool = False) -> dict[str, Any]:
    return {
        "type": "callable",
        "job_key": job_key,
        "fn": fn,
        "invalidate_cache": invalidate_cache,
    }


def _maintenance_job(job_key: str) -> dict[str, Any]:
    return {
        "type": "maintenance",
        "job_key": job_key,
        "invalidate_cache": False,
    }


def _collect_news_bundle(db: Session):
    counts = empty_counts()
    errors: list[str] = []
    for fn in (collect_finnhub_news, collect_fed_rss):
        try:
            add_counts(counts, fn(db))
        except Exception as exc:
            errors.append(str(exc))
    if counts["fetched_count"] == 0 and errors:
        raise RuntimeError("; ".join(errors))
    return counts


def _collect_us_global_market_bundle(db: Session):
    counts = empty_counts()
    errors: list[str] = []
    for fn in (collect_equity_indices, collect_real_economy):
        try:
            add_counts(counts, fn(db))
        except Exception as exc:
            errors.append(str(exc))
    if counts["fetched_count"] == 0 and errors:
        raise RuntimeError("; ".join(errors))
    return counts


def _compute_snapshots(db: Session):
    from ..workers.snapshot_worker import compute_snapshots

    return compute_snapshots(db)


def _enqueue_daily_insight_if_missing(db: Session) -> dict[str, Any]:
    if not settings.AI_DAILY_INSIGHT_ENABLED:
        return {
            "job_key": "daily_insight_enqueue",
            "status": "skipped",
            "reason": "ai_daily_insight_disabled",
            "fetched_count": 0,
            "inserted_count": 0,
            "updated_count": 0,
        }
    as_of_date = get_today_kst()
    existing = get_existing_daily_insight(db, as_of_date)
    if existing and existing.status == "success":
        return {
            "job_key": "daily_insight_enqueue",
            "status": "skipped",
            "reason": "already_succeeded_today",
            "fetched_count": 0,
            "inserted_count": 0,
            "updated_count": 0,
        }

    try:
        from ..workers.celery_app import celery

        celery.send_task("app.workers.celery_app.task_ensure_daily_insight")
        return {
            "job_key": "daily_insight_enqueue",
            "status": "queued",
            "reason": "missing_success_row",
            "fetched_count": 0,
            "inserted_count": 0,
            "updated_count": 0,
        }
    except Exception as exc:
        return {
            "job_key": "daily_insight_enqueue",
            "status": "failed",
            "reason": str(exc),
            "fetched_count": 0,
            "inserted_count": 0,
            "updated_count": 0,
        }


def _invalidate_dashboard_cache():
    try:
        cache_delete_sync("summary:v1")
    except Exception as exc:
        logger.warning("Failed to invalidate dashboard cache after batch: %s", exc)


def _invalidate_calendar_cache():
    try:
        cache_delete_pattern_sync("calendar:*")
    except Exception as exc:
        logger.warning("Failed to invalidate calendar cache after batch: %s", exc)


def _all_job_definitions() -> list[dict[str, Any]]:
    return [
        _guarded_job("fred_rates", "fred", lambda session: collect_rates(session)),
        _guarded_job("fred_macro", "fred", lambda session: collect_macro(session)),
        _guarded_job("credit_spreads", "fred", lambda session: collect_credit_spreads(session)),
        _guarded_job("equity_us_global", "yfinance", lambda session: _collect_us_global_market_bundle(session)),
        _guarded_job(
            "equity_asia",
            "yfinance",
            lambda session: collect_equity_indices(session, tickers=ASIA_EQUITY_TICKERS),
        ),
        _guarded_job("sector_performance", "yfinance", lambda session: collect_sectors(session)),
        _guarded_job("fedwatch", "cme", lambda session: collect_fedwatch(session)),
        _guarded_job("fx_rates", "exchangerate-api", lambda session: collect_exchange_rates(session)),
        _guarded_job("news", "news", lambda session: _collect_news_bundle(session)),
        _guarded_job("snapshot_compute", "internal", lambda session: _compute_snapshots(session)),
        _guarded_job("calendar_events", "calendar", lambda session: collect_calendar_events(session)),
        _guarded_job("fomc_calendar", "federalreserve", lambda session: collect_fomc_calendar(session)),
        _guarded_job("fed_communications", "federalreserve", lambda session: collect_fed_communications(session)),
    ]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
