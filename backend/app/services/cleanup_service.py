from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.database import SessionLocal
from ..models.indicators import (
    AiSummary,
    ChangeSnapshot,
    CleanupRun,
    DivergenceEvent,
    DivergenceReport,
    InterestRate,
    NewsItem,
    SentimentSignal,
)

logger = logging.getLogger(__name__)


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass(frozen=True)
class CleanupPolicy:
    collection_success_log_retention_days: int = 90
    collection_failure_log_retention_days: int = 180
    raw_response_retention_days: int = 30
    debug_log_retention_days: int = 30
    scheduler_log_retention_days: int = 30
    enable_raw_response_storage: bool = False

    @classmethod
    def from_settings(cls) -> "CleanupPolicy":
        return cls(
            collection_success_log_retention_days=settings.COLLECTION_SUCCESS_LOG_RETENTION_DAYS,
            collection_failure_log_retention_days=settings.COLLECTION_FAILURE_LOG_RETENTION_DAYS,
            raw_response_retention_days=settings.RAW_RESPONSE_RETENTION_DAYS,
            debug_log_retention_days=settings.DEBUG_LOG_RETENTION_DAYS,
            scheduler_log_retention_days=settings.SCHEDULER_LOG_RETENTION_DAYS,
            enable_raw_response_storage=settings.ENABLE_RAW_RESPONSE_STORAGE,
        )


def _table_exists(table_names: set[str], table_name: str) -> bool:
    return table_name in table_names


def _delete_in_batches(
    db: Session,
    model,
    timestamp_column,
    cutoff: datetime,
    *filters,
    batch_size: int = 1000,
) -> int:
    deleted_total = 0
    while True:
        ids = [
            row_id
            for (row_id,) in (
                db.query(model.id)
                .filter(timestamp_column < cutoff, *filters)
                .order_by(model.id)
                .limit(batch_size)
                .all()
            )
        ]
        if not ids:
            break
        deleted_total += (
            db.query(model)
            .filter(model.id.in_(ids))
            .delete(synchronize_session=False)
        )
        db.flush()
    return deleted_total


def run_cleanup(
    db: Session,
    *,
    now: datetime | None = None,
    policy: CleanupPolicy | None = None,
) -> dict:
    started_at = now or _utcnow_naive()
    policy = policy or CleanupPolicy.from_settings()

    result = {
        "collection_success_logs_deleted": 0,
        "collection_failure_logs_deleted": 0,
        "raw_responses_deleted": 0,
        "debug_logs_deleted": 0,
        "scheduler_logs_deleted": 0,
        "started_at": started_at.isoformat(),
        "finished_at": None,
    }
    table_names = set(inspect(db.get_bind()).get_table_names())

    try:
        # news_items is the closest existing collected payload/log table.
        if _table_exists(table_names, NewsItem.__tablename__):
            success_cutoff = started_at - timedelta(days=policy.collection_success_log_retention_days)
            failure_cutoff = started_at - timedelta(days=policy.collection_failure_log_retention_days)
            result["collection_success_logs_deleted"] = _delete_in_batches(
                db,
                NewsItem,
                NewsItem.collected_at,
                success_cutoff,
                NewsItem.sentiment_extracted.is_(True),
            )
            result["collection_failure_logs_deleted"] = _delete_in_batches(
                db,
                NewsItem,
                NewsItem.collected_at,
                failure_cutoff,
                NewsItem.sentiment_extracted.is_(False),
            )

        # No persistent raw response table currently exists.
        result["raw_responses_deleted"] = 0

        debug_cutoff = started_at - timedelta(days=policy.debug_log_retention_days)
        debug_targets = [
            (ChangeSnapshot, ChangeSnapshot.snapshot_date),
            (SentimentSignal, SentimentSignal.extracted_at),
            (DivergenceEvent, DivergenceEvent.detected_at),
            (DivergenceReport, DivergenceReport.generated_at),
        ]
        for model, timestamp_column in debug_targets:
            if _table_exists(table_names, model.__tablename__):
                result["debug_logs_deleted"] += _delete_in_batches(
                    db,
                    model,
                    timestamp_column,
                    debug_cutoff,
                )

        scheduler_cutoff = started_at - timedelta(days=policy.scheduler_log_retention_days)
        if _table_exists(table_names, AiSummary.__tablename__):
            result["scheduler_logs_deleted"] = _delete_in_batches(
                db,
                AiSummary,
                AiSummary.created_at,
                scheduler_cutoff,
            )
        if _table_exists(table_names, CleanupRun.__tablename__):
            _delete_in_batches(
                db,
                CleanupRun,
                CleanupRun.created_at,
                scheduler_cutoff,
            )

        # Explicitly excluded: core observation time series such as interest_rates and peers.
        if _table_exists(table_names, InterestRate.__tablename__):
            db.query(InterestRate.id).limit(1).all()

        if _table_exists(table_names, CleanupRun.__tablename__):
            db.add(
                CleanupRun(
                    started_at=started_at,
                    finished_at=started_at,
                    collection_success_logs_deleted=result["collection_success_logs_deleted"],
                    collection_failure_logs_deleted=result["collection_failure_logs_deleted"],
                    raw_responses_deleted=result["raw_responses_deleted"],
                    debug_logs_deleted=result["debug_logs_deleted"],
                    scheduler_logs_deleted=result["scheduler_logs_deleted"],
                    result_json=result,
                )
            )

        db.commit()
        db.expire_all()
    except Exception:
        db.rollback()
        raise

    finished_at = _utcnow_naive()
    result["finished_at"] = finished_at.isoformat()
    if _table_exists(table_names, CleanupRun.__tablename__):
        latest = db.query(CleanupRun).order_by(CleanupRun.id.desc()).first()
        if latest:
            latest.finished_at = finished_at
            latest.result_json = result
            db.commit()
            db.expire(latest)
    logger.info("cleanup completed: %s", json.dumps(result, ensure_ascii=False))
    return result


def main() -> int:
    db = SessionLocal()
    try:
        result = run_cleanup(db)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
