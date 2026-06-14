from __future__ import annotations

import logging
import threading
import uuid
import zlib
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable

from sqlalchemy import desc, text
from sqlalchemy.orm import Session

from ..core.config import settings
from ..models import CollectionRun

logger = logging.getLogger(__name__)

_LOCAL_LOCK = threading.Lock()
_LOCKED_JOB_KEYS: set[str] = set()


def should_run(
    db: Session,
    job_key: str,
    min_interval_minutes: int,
    target_date=None,
) -> dict[str, Any]:
    if not settings.COLLECTION_GUARD_ENABLED:
        return {
            "should_run": True,
            "reason": None,
            "target_date": _normalize_target_date(target_date),
        }

    normalized_target_date = _normalize_target_date(target_date)
    latest_success = (
        db.query(CollectionRun)
        .filter(
            CollectionRun.job_key == job_key,
            CollectionRun.status == "success",
        )
        .order_by(desc(CollectionRun.finished_at), desc(CollectionRun.id))
        .first()
    )

    if latest_success and latest_success.finished_at:
        cutoff = _utcnow_naive() - timedelta(minutes=min_interval_minutes)
        if latest_success.finished_at >= cutoff:
            return {
                "should_run": False,
                "reason": "min_interval_not_elapsed",
                "target_date": normalized_target_date,
            }

    return {
        "should_run": True,
        "reason": None,
        "target_date": normalized_target_date,
    }


def start_run(
    db: Session,
    job_key: str,
    provider: str,
    target_date,
    min_interval_minutes: int,
) -> CollectionRun:
    run = CollectionRun(
        job_key=job_key,
        provider=provider,
        target_date=_normalize_target_date(target_date),
        status="running",
        started_at=_utcnow_naive(),
        min_interval_minutes=min_interval_minutes,
        fetched_count=0,
        inserted_count=0,
        updated_count=0,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def finish_run(
    db: Session,
    run_id: int,
    status: str,
    counts: dict[str, int] | None = None,
    error_message: str | None = None,
) -> CollectionRun:
    run = db.query(CollectionRun).filter(CollectionRun.id == run_id).first()
    if run is None:
        raise ValueError(f"CollectionRun {run_id} not found")

    count_values = _normalize_counts(counts)
    run.status = status
    run.finished_at = _utcnow_naive()
    run.fetched_count = count_values["fetched_count"]
    run.inserted_count = count_values["inserted_count"]
    run.updated_count = count_values["updated_count"]
    run.error_message = error_message
    db.commit()
    db.refresh(run)
    return run


def run_with_guard(
    db: Session,
    job_key: str,
    provider: str,
    min_interval_minutes: int,
    fn: Callable[[Session], Any],
    *,
    target_date=None,
) -> dict[str, Any]:
    normalized_target_date = _normalize_target_date(target_date) or _utcnow_naive().date()

    if not settings.COLLECTION_GUARD_ENABLED:
        try:
            result = fn(db)
            if isinstance(result, dict) and result.get("status") in {"skipped", "failed"}:
                counts = _normalize_counts(result)
                return _result_payload(job_key, result["status"], counts=counts, reason=result.get("reason"))
            counts = _normalize_counts(result if isinstance(result, dict) else None)
            return _result_payload(job_key, "success", counts=counts)
        except Exception as exc:
            logger.exception("Collection job failed without guard: %s", job_key)
            return _result_payload(job_key, "failed", reason=str(exc))

    with _job_lock(db, job_key) as lock_info:
        if not lock_info["acquired"]:
            _record_skipped_run(
                db,
                job_key=job_key,
                provider=provider,
                target_date=normalized_target_date,
                min_interval_minutes=min_interval_minutes,
                reason="lock_not_acquired",
            )
            return _result_payload(job_key, "skipped", reason="lock_not_acquired")

        decision = should_run(
            db,
            job_key=job_key,
            min_interval_minutes=min_interval_minutes,
            target_date=normalized_target_date,
        )
        if not decision["should_run"]:
            _record_skipped_run(
                db,
                job_key=job_key,
                provider=provider,
                target_date=normalized_target_date,
                min_interval_minutes=min_interval_minutes,
                reason=decision["reason"],
            )
            return _result_payload(job_key, "skipped", reason=decision["reason"])

        run = start_run(
            db,
            job_key=job_key,
            provider=provider,
            target_date=normalized_target_date,
            min_interval_minutes=min_interval_minutes,
        )
        try:
            result = fn(db)
            if isinstance(result, dict) and result.get("status") in {"skipped", "failed"}:
                counts = _normalize_counts(result)
                finish_run(db, run.id, result["status"], counts=counts, error_message=result.get("reason"))
                return _result_payload(job_key, result["status"], counts=counts, reason=result.get("reason"))
            counts = _normalize_counts(result if isinstance(result, dict) else None)
            finish_run(db, run.id, "success", counts=counts)
            return _result_payload(job_key, "success", counts=counts)
        except Exception as exc:
            logger.exception("Collection job failed: %s", job_key)
            db.rollback()
            finish_run(db, run.id, "failed", error_message=str(exc))
            return _result_payload(job_key, "failed", reason=str(exc))


def get_default_min_interval(job_key: str) -> int:
    mapping = {
        "fred_rates": settings.FRED_MIN_INTERVAL_MINUTES,
        "fred_macro": settings.FRED_MIN_INTERVAL_MINUTES,
        "credit_spreads": settings.FRED_MIN_INTERVAL_MINUTES,
        "fx_rates": settings.FX_MIN_INTERVAL_MINUTES,
        "equity_us_global": settings.EQUITY_MIN_INTERVAL_MINUTES,
        "equity_asia": settings.EQUITY_MIN_INTERVAL_MINUTES,
        "sector_performance": settings.EQUITY_MIN_INTERVAL_MINUTES,
        "fedwatch": settings.FEDWATCH_MIN_INTERVAL_MINUTES,
        "news": settings.NEWS_MIN_INTERVAL_MINUTES,
        "fomc_calendar": settings.FOMC_MIN_INTERVAL_MINUTES,
        "fed_communications": settings.COMMUNICATION_MIN_INTERVAL_MINUTES,
        "calendar_events": settings.CALENDAR_MIN_INTERVAL_MINUTES,
        "snapshot_compute": settings.SNAPSHOT_MIN_INTERVAL_MINUTES,
    }
    return mapping[job_key]


@contextmanager
def _job_lock(db: Session, job_key: str):
    if settings.COLLECTION_LOCK_BACKEND == "redis":
        try:
            import redis

            lock_key = f"collection_guard:{job_key}"
            token = str(uuid.uuid4())
            client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
            acquired = bool(client.set(lock_key, token, nx=True, ex=600))
            try:
                yield {"acquired": acquired, "lock_id": lock_key}
            finally:
                if acquired and client.get(lock_key) == token:
                    client.delete(lock_key)
            return
        except Exception as exc:
            logger.warning("Redis lock backend unavailable for %s; falling back to local lock: %s", job_key, exc)

    if settings.COLLECTION_LOCK_BACKEND == "postgres" and db.get_bind().dialect.name == "postgresql":
        lock_id = int(zlib.crc32(job_key.encode("utf-8")))
        acquired = bool(
            db.execute(text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": lock_id}).scalar()
        )
        try:
            yield {"acquired": acquired, "lock_id": lock_id}
        finally:
            if acquired:
                db.execute(text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": lock_id})
                db.commit()
        return

    acquired = False
    with _LOCAL_LOCK:
        if job_key not in _LOCKED_JOB_KEYS:
            _LOCKED_JOB_KEYS.add(job_key)
            acquired = True
    try:
        yield {"acquired": acquired, "lock_id": None}
    finally:
        if acquired:
            with _LOCAL_LOCK:
                _LOCKED_JOB_KEYS.discard(job_key)


def _record_skipped_run(
    db: Session,
    *,
    job_key: str,
    provider: str,
    target_date: date | None,
    min_interval_minutes: int,
    reason: str,
) -> None:
    now = _utcnow_naive()
    db.add(
        CollectionRun(
            job_key=job_key,
            provider=provider,
            target_date=target_date,
            status="skipped",
            started_at=now,
            finished_at=now,
            min_interval_minutes=min_interval_minutes,
            fetched_count=0,
            inserted_count=0,
            updated_count=0,
            error_message=reason,
        )
    )
    db.commit()


def _result_payload(
    job_key: str,
    status: str,
    *,
    counts: dict[str, int] | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    payload = {
        "job_key": job_key,
        "status": status,
        "fetched_count": 0,
        "inserted_count": 0,
        "updated_count": 0,
    }
    count_values = _normalize_counts(counts)
    payload.update(count_values)
    if reason:
        payload["reason"] = reason
    return payload


def _normalize_counts(counts: dict[str, Any] | None) -> dict[str, int]:
    counts = counts or {}
    return {
        "fetched_count": int(counts.get("fetched_count", 0) or 0),
        "inserted_count": int(counts.get("inserted_count", 0) or 0),
        "updated_count": int(counts.get("updated_count", 0) or 0),
    }


def _normalize_target_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return None
    return None


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
