"""Celery application and scheduled collection batches."""
import logging
from celery import Celery
from celery.schedules import crontab

from ..core.config import settings
from ..core.database import SessionLocal
from ..services.cleanup_service import run_cleanup
from ..services.collection_orchestrator import (
    run_evening_batch,
    run_guarded_job,
    run_morning_batch,
    run_noon_batch,
    run_weekly_batch,
)
from .ai_worker import generate_daily_summary
from .sentiment_worker import run_daily_sentiment_pipeline

logger = logging.getLogger(__name__)
celery = Celery("macro", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
    # Celery beat interprets these crontab values in `timezone` above, not raw UTC.
    # That lets us express schedules directly in KST while keeping enable_utc on.
    beat_schedule={
        "morning-batch": {
            "task": "app.workers.celery_app.task_run_morning_batch",
            "schedule": crontab(hour=7, minute=30),
        },
        "noon-batch": {
            "task": "app.workers.celery_app.task_run_noon_batch",
            "schedule": crontab(hour=12, minute=30),
        },
        "evening-batch": {
            "task": "app.workers.celery_app.task_run_evening_batch",
            "schedule": crontab(hour=18, minute=30),
        },
        "weekly-batch": {
            "task": "app.workers.celery_app.task_run_weekly_batch",
            "schedule": crontab(day_of_week=1, hour=8, minute=0),
        },
        "cleanup-retention-data": {
            "task": "app.workers.celery_app.task_cleanup_retention",
            "schedule": crontab(hour=3, minute=5),
        },
    },
)


def _with_db(fn, *args, **kwargs):
    db = SessionLocal()
    try:
        return fn(db, *args, **kwargs)
    finally:
        db.close()


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


@celery.task(name="app.workers.celery_app.task_compute_snapshots")
def task_compute_snapshots():
    return _with_db(run_guarded_job, "snapshot_compute")


@celery.task(name="app.workers.celery_app.task_ai_summary")
def task_ai_summary():
    db = SessionLocal()
    try:
        generate_daily_summary(db)
        return {"status": "success", "job_key": "ai_summary"}
    finally:
        db.close()


@celery.task(name="app.workers.celery_app.task_sentiment_pipeline")
def task_sentiment_pipeline():
    """Daily sentiment batch pipeline (extract → update → detect chain)."""
    run_daily_sentiment_pipeline()
    return {"status": "success", "job_key": "sentiment_pipeline"}


@celery.task(name="app.workers.celery_app.task_cleanup_retention")
def task_cleanup_retention():
    return _with_db(run_cleanup)
