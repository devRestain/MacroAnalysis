"""Celery application and scheduled collection batches."""
import logging
from celery import Celery
from celery.schedules import crontab

from ..core.config import settings
from ..core.database import SessionLocal
from ..services.cleanup_service import run_cleanup
from ..services.collection_orchestrator import (
    run_calendar_batch,
    run_evening_batch,
    run_guarded_job,
    run_morning_batch,
    run_noon_batch,
    run_weekly_batch,
)
from ..services.daily_insight_service import daily_insight_to_summary_response, ensure_daily_insight
from .sentiment_worker import run_daily_sentiment_pipeline

logger = logging.getLogger(__name__)
celery = Celery("macro", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

beat_schedule = {
    "cleanup-retention-data": {
        "task": "app.workers.celery_app.task_cleanup_retention",
        "schedule": crontab(hour=3, minute=5),
    },
}

if settings.MORNING_BATCH_ENABLED:
    beat_schedule["morning-batch"] = {
        "task": "app.workers.celery_app.task_run_morning_batch",
        "schedule": crontab(hour=7, minute=30),
    }
if settings.NOON_BATCH_ENABLED:
    beat_schedule["noon-batch"] = {
        "task": "app.workers.celery_app.task_run_noon_batch",
        "schedule": crontab(hour=12, minute=30),
    }
if settings.EVENING_BATCH_ENABLED:
    beat_schedule["evening-batch"] = {
        "task": "app.workers.celery_app.task_run_evening_batch",
        "schedule": crontab(hour=18, minute=30),
    }
if settings.WEEKLY_BATCH_ENABLED:
    beat_schedule["weekly-batch"] = {
        "task": "app.workers.celery_app.task_run_weekly_batch",
        "schedule": crontab(day_of_week=1, hour=8, minute=0),
    }
if settings.SENTIMENT_PIPELINE_ENABLED:
    beat_schedule["sentiment-pipeline"] = {
        "task": "app.workers.celery_app.task_sentiment_pipeline",
        "schedule": crontab(
            hour=settings.SENTIMENT_PIPELINE_HOUR_KST,
            minute=settings.SENTIMENT_PIPELINE_MINUTE_KST,
        ),
    }
beat_schedule["calendar-events-batch"] = {
    "task": "app.workers.celery_app.task_collect_calendar_events",
    "schedule": crontab(hour=8, minute=10),
}

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
    # Celery beat interprets these crontab values in `timezone` above, not raw UTC.
    # That lets us express schedules directly in KST while keeping enable_utc on.
    beat_schedule=beat_schedule,
)


def _with_db(fn, *args, **kwargs):
    db = SessionLocal()
    try:
        return fn(db, *args, **kwargs)
    finally:
        db.close()


def _serialize_task_result(result):
    if isinstance(result, dict):
        return result
    if hasattr(result, "as_of_date") and hasattr(result, "status"):
        payload = daily_insight_to_summary_response(result)
        payload["as_of_date"] = result.as_of_date.isoformat()
        return payload
    return result


@celery.task(name="app.workers.celery_app.task_run_morning_batch")
def task_run_morning_batch():
    return _with_db(run_morning_batch)


@celery.task(name="app.workers.celery_app.task_run_noon_batch")
def task_run_noon_batch():
    return _with_db(run_noon_batch)


@celery.task(name="app.workers.celery_app.task_run_evening_batch")
def task_run_evening_batch():
    return _with_db(run_evening_batch)


@celery.task(name="app.workers.celery_app.task_run_weekly_batch")
def task_run_weekly_batch():
    return _with_db(run_weekly_batch)


# Individual guarded tasks stay available for debugging or manual use.
@celery.task(name="app.workers.celery_app.task_collect_fx")
def task_collect_fx():
    return _with_db(run_guarded_job, "fx_rates")


@celery.task(name="app.workers.celery_app.task_collect_equity")
def task_collect_equity():
    return _with_db(run_guarded_job, "equity_us_global")


@celery.task(name="app.workers.celery_app.task_collect_equity_asia")
def task_collect_equity_asia():
    return _with_db(run_guarded_job, "equity_asia")


@celery.task(name="app.workers.celery_app.task_collect_fred_rates")
def task_collect_fred_rates():
    return _with_db(run_guarded_job, "fred_rates")


@celery.task(name="app.workers.celery_app.task_collect_fred_macro")
def task_collect_fred_macro():
    return _with_db(run_guarded_job, "fred_macro")


@celery.task(name="app.workers.celery_app.task_collect_credit_spreads")
def task_collect_credit_spreads():
    return _with_db(run_guarded_job, "credit_spreads")


@celery.task(name="app.workers.celery_app.task_collect_sectors")
def task_collect_sectors():
    return _with_db(run_guarded_job, "sector_performance")


@celery.task(name="app.workers.celery_app.task_collect_fedwatch")
def task_collect_fedwatch():
    return _with_db(run_guarded_job, "fedwatch")


@celery.task(name="app.workers.celery_app.task_collect_news")
def task_collect_news():
    return _with_db(run_guarded_job, "news")


@celery.task(name="app.workers.celery_app.task_collect_fomc")
def task_collect_fomc():
    return _with_db(run_guarded_job, "fomc_calendar")


@celery.task(name="app.workers.celery_app.task_collect_calendar_events")
def task_collect_calendar_events():
    return _with_db(run_calendar_batch)


@celery.task(name="app.workers.celery_app.task_compute_snapshots")
def task_compute_snapshots():
    return _with_db(run_guarded_job, "snapshot_compute")


@celery.task(name="app.workers.celery_app.task_ai_summary")
def task_ai_summary():
    return _serialize_task_result(_with_db(ensure_daily_insight, force=False))


@celery.task(name="app.workers.celery_app.task_ensure_daily_insight")
def task_ensure_daily_insight():
    return _serialize_task_result(_with_db(ensure_daily_insight, force=False))


@celery.task(name="app.workers.celery_app.task_sentiment_pipeline")
def task_sentiment_pipeline():
    """Daily sentiment batch pipeline (extract → update → detect chain)."""
    result = run_daily_sentiment_pipeline()
    if result.get("skipped"):
        result["job_key"] = "sentiment_pipeline"
        return result
    return {"status": "success", "job_key": "sentiment_pipeline", **result}


@celery.task(name="app.workers.celery_app.task_cleanup_retention")
def task_cleanup_retention():
    return _with_db(run_cleanup)
