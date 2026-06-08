"""Celery application and scheduled tasks."""
import logging
import redis
from celery import Celery
from celery.schedules import crontab
from ..core.config import settings
from ..core.database import SessionLocal
from ..collectors.fred_collector import collect_rates, collect_macro, collect_credit_spreads
from ..collectors.market_collector import collect_equity_indices, collect_sectors, collect_real_economy
from ..collectors.fx_collector import collect_exchange_rates
from ..collectors.news_collector import collect_finnhub_news, collect_fed_rss
from ..collectors.fomc_collector import collect_fomc_calendar, collect_fedwatch
from ..services.cleanup_service import run_cleanup
from .snapshot_worker import compute_snapshots
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
    beat_schedule={
        # FX — 09:00 KST (00:00 UTC)
        "collect-fx": {
            "task": "app.workers.celery_app.task_collect_fx",
            "schedule": crontab(hour=0, minute=0),
        },
        # US equity close — 07:00 KST (22:00 UTC prev day)
        "collect-us-equity": {
            "task": "app.workers.celery_app.task_collect_equity",
            "schedule": crontab(hour=22, minute=0),
        },
        # KR equity close — 16:00 KST (07:00 UTC)
        "collect-kr-equity": {
            "task": "app.workers.celery_app.task_collect_equity",
            "schedule": crontab(hour=7, minute=0),
        },
        # FRED macro — 06:00 KST (21:00 UTC prev day)
        "collect-fred-macro": {
            "task": "app.workers.celery_app.task_collect_fred",
            "schedule": crontab(hour=21, minute=0),
        },
        # Sectors — 07:30 KST (22:30 UTC prev day)
        "collect-sectors": {
            "task": "app.workers.celery_app.task_collect_sectors",
            "schedule": crontab(hour=22, minute=30),
        },
        # FedWatch — 08:00 KST (23:00 UTC prev day)
        "collect-fedwatch": {
            "task": "app.workers.celery_app.task_collect_fedwatch",
            "schedule": crontab(hour=23, minute=0),
        },
        # News — every hour
        "collect-news": {
            "task": "app.workers.celery_app.task_collect_news",
            "schedule": crontab(minute=0),
        },
        # FOMC calendar — every Monday 08:00 KST (23:00 UTC Sunday)
        "collect-fomc-calendar": {
            "task": "app.workers.celery_app.task_collect_fomc",
            "schedule": crontab(day_of_week=0, hour=23, minute=0),
        },
        # Snapshots — 07:00 KST (22:00 UTC) after market close
        "compute-snapshots": {
            "task": "app.workers.celery_app.task_compute_snapshots",
            "schedule": crontab(hour=22, minute=15),
        },
        # AI Summary — 06:30 KST (21:30 UTC prev day)
        "generate-ai-summary": {
            "task": "app.workers.celery_app.task_ai_summary",
            "schedule": crontab(hour=21, minute=30),
        },
        # Sentiment pipeline — 22:00 UTC (07:00 KST) daily batch
        # 뉴스 수집이 완료된 후 하루 1회 일괄 처리
        "daily-sentiment-pipeline": {
            "task": "app.workers.celery_app.task_sentiment_pipeline",
            "schedule": crontab(hour=22, minute=45),
        },
        # Cleanup — 03:05 KST (18:05 UTC prev day)
        "cleanup-retention-data": {
            "task": "app.workers.celery_app.task_cleanup_retention",
            "schedule": crontab(hour=18, minute=5),
        },
    },
)


def _with_db(fn, *args, **kwargs):
    db = SessionLocal()
    try:
        return fn(db, *args, **kwargs)
    finally:
        db.close()


def _invalidate_dashboard_cache():
    try:
        redis.Redis.from_url(settings.REDIS_URL, decode_responses=True).delete("summary:v1")
    except Exception as exc:
        logger.warning("Failed to invalidate dashboard cache: %s", exc)


@celery.task(name="app.workers.celery_app.task_collect_fx")
def task_collect_fx():
    _with_db(collect_exchange_rates)
    _invalidate_dashboard_cache()


@celery.task(name="app.workers.celery_app.task_collect_equity")
def task_collect_equity():
    _with_db(collect_equity_indices)
    _with_db(collect_real_economy)
    _invalidate_dashboard_cache()


@celery.task(name="app.workers.celery_app.task_collect_fred")
def task_collect_fred():
    _with_db(collect_rates)
    _with_db(collect_macro)
    _with_db(collect_credit_spreads)
    _invalidate_dashboard_cache()


@celery.task(name="app.workers.celery_app.task_collect_sectors")
def task_collect_sectors():
    _with_db(collect_sectors)
    _invalidate_dashboard_cache()


@celery.task(name="app.workers.celery_app.task_collect_fedwatch")
def task_collect_fedwatch():
    _with_db(collect_fedwatch)
    _invalidate_dashboard_cache()


@celery.task(name="app.workers.celery_app.task_collect_news")
def task_collect_news():
    _with_db(collect_finnhub_news)
    _with_db(collect_fed_rss)
    _invalidate_dashboard_cache()


@celery.task(name="app.workers.celery_app.task_collect_fomc")
def task_collect_fomc():
    _with_db(collect_fomc_calendar)
    _invalidate_dashboard_cache()


@celery.task(name="app.workers.celery_app.task_compute_snapshots")
def task_compute_snapshots():
    _with_db(compute_snapshots)
    _invalidate_dashboard_cache()


@celery.task(name="app.workers.celery_app.task_ai_summary")
def task_ai_summary():
    _with_db(generate_daily_summary)
    _invalidate_dashboard_cache()


@celery.task(name="app.workers.celery_app.task_sentiment_pipeline")
def task_sentiment_pipeline():
    """일일 sentiment 배치 파이프라인 (extract → update → detect chain)."""
    run_daily_sentiment_pipeline()


@celery.task(name="app.workers.celery_app.task_cleanup_retention")
def task_cleanup_retention():
    _with_db(run_cleanup)
