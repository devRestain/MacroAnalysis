from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Callable

import redis
from sqlalchemy.orm import Session

from ..collectors.fomc_collector import collect_fedwatch, collect_fomc_calendar
from ..collectors.fred_collector import collect_credit_spreads, collect_macro, collect_rates
from ..collectors.fx_collector import collect_exchange_rates
from ..collectors.market_collector import collect_equity_indices, collect_real_economy, collect_sectors
from ..collectors.news_collector import collect_fed_rss, collect_finnhub_news
from ..core.config import settings
from .collection_guard import get_default_min_interval, run_with_guard
from ..workers.snapshot_worker import compute_snapshots

logger = logging.getLogger(__name__)

ASIA_EQUITY_TICKERS = ["^KS11", "^N225", "^SSEC"]


def run_morning_batch(db: Session) -> dict[str, Any]:
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
        _guarded_job("snapshot_compute", "internal", lambda session: compute_snapshots(session)),
        _placeholder_job("daily_insight_trigger", "pending_request_3"),
    ]
    return _run_batch(db, "morning", jobs)


def run_noon_batch(db: Session) -> dict[str, Any]:
    jobs = [
        _guarded_job("news", "news", lambda session: _collect_news_bundle(session)),
        _guarded_job("fx_rates", "exchangerate-api", lambda session: collect_exchange_rates(session)),
        _guarded_job("snapshot_compute", "internal", lambda session: compute_snapshots(session)),
    ]
    return _run_batch(db, "noon", jobs)


def run_evening_batch(db: Session) -> dict[str, Any]:
    jobs = [
        _guarded_job(
            "equity_asia",
            "yfinance",
            lambda session: collect_equity_indices(session, tickers=ASIA_EQUITY_TICKERS),
        ),
        _guarded_job("fx_rates", "exchangerate-api", lambda session: collect_exchange_rates(session)),
        _guarded_job("news", "news", lambda session: _collect_news_bundle(session)),
        _guarded_job("snapshot_compute", "internal", lambda session: compute_snapshots(session)),
    ]
    return _run_batch(db, "evening", jobs)


def run_weekly_batch(db: Session) -> dict[str, Any]:
    jobs = [
        _guarded_job("fomc_calendar", "federalreserve", lambda session: collect_fomc_calendar(session)),
        _maintenance_job("collection_runs_maintenance"),
    ]
    return _run_batch(db, "weekly", jobs)


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

    return {
        "batch": batch_name,
        "started_at": started_at.isoformat(),
        "finished_at": _utcnow().isoformat(),
        "jobs": results,
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
        "invalidate_cache": job_key in {"snapshot_compute", "fred_rates", "fred_macro", "credit_spreads", "equity_us_global", "equity_asia", "sector_performance", "fedwatch", "fx_rates", "news", "fomc_calendar"},
    }


def _placeholder_job(job_key: str, reason: str) -> dict[str, Any]:
    return {
        "type": "placeholder",
        "job_key": job_key,
        "reason": reason,
        "invalidate_cache": False,
    }


def _maintenance_job(job_key: str) -> dict[str, Any]:
    return {
        "type": "maintenance",
        "job_key": job_key,
        "invalidate_cache": False,
    }


def _collect_news_bundle(db: Session):
    collect_finnhub_news(db)
    collect_fed_rss(db)


def _collect_us_global_market_bundle(db: Session):
    collect_equity_indices(db)
    collect_real_economy(db)


def _invalidate_dashboard_cache():
    try:
        redis.Redis.from_url(settings.REDIS_URL, decode_responses=True).delete("summary:v1")
    except Exception as exc:
        logger.warning("Failed to invalidate dashboard cache after batch: %s", exc)


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
        _guarded_job("snapshot_compute", "internal", lambda session: compute_snapshots(session)),
        _guarded_job("fomc_calendar", "federalreserve", lambda session: collect_fomc_calendar(session)),
    ]


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None, microsecond=0)
