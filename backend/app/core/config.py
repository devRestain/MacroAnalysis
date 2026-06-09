from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache


RETENTION_DEFAULTS = {
    "COLLECTION_SUCCESS_LOG_RETENTION_DAYS": 90,
    "COLLECTION_FAILURE_LOG_RETENTION_DAYS": 180,
    "RAW_RESPONSE_RETENTION_DAYS": 30,
    "DEBUG_LOG_RETENTION_DAYS": 30,
    "SCHEDULER_LOG_RETENTION_DAYS": 30,
}


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://macro:macro@postgres:5432/macrodb"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # API Keys
    FRED_API_KEY: str = ""
    FINNHUB_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    EXCHANGERATE_API_KEY: str = ""
    NEWS_API_KEY: str = ""

    # App
    APP_ENV: str = "production"
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:80"]

    # AI
    AI_MODEL: str = "gpt-4o-mini"
    AI_SUMMARY_HOUR_KST: int = 6  # 06:30 KST

    # Sentiment Pipeline (v2)
    SENTIMENT_PIPELINE_ENABLED: bool = True
    SENTIMENT_PIPELINE_HOUR_KST: int = 22
    SENTIMENT_PIPELINE_MINUTE_KST: int = 5
    SENTIMENT_BATCH_SIZE: int = 20
    SENTIMENT_MAX_NEWS_ITEMS_PER_RUN: int = 40
    SENTIMENT_LOOKBACK_DAYS: int = 7
    SENTIMENT_REPORTS_ENABLED: bool = False
    FOMC_SENTIMENT_ENABLED: bool = True
    FOMC_SENTIMENT_LOOKBACK_DAYS: int = 30
    FOMC_SENTIMENT_MIN_TEXT_LENGTH: int = 500
    FOMC_SENTIMENT_PENDING_TTL_HOURS: int = 24
    INERTIA_ALPHA: float = 0.05
    DIVERGENCE_WARNING_THRESHOLD: float = 0.25
    DIVERGENCE_ALERT_THRESHOLD: float = 0.40

    # Retention / Cleanup
    COLLECTION_SUCCESS_LOG_RETENTION_DAYS: int = RETENTION_DEFAULTS["COLLECTION_SUCCESS_LOG_RETENTION_DAYS"]
    COLLECTION_FAILURE_LOG_RETENTION_DAYS: int = RETENTION_DEFAULTS["COLLECTION_FAILURE_LOG_RETENTION_DAYS"]
    RAW_RESPONSE_RETENTION_DAYS: int = RETENTION_DEFAULTS["RAW_RESPONSE_RETENTION_DAYS"]
    DEBUG_LOG_RETENTION_DAYS: int = RETENTION_DEFAULTS["DEBUG_LOG_RETENTION_DAYS"]
    SCHEDULER_LOG_RETENTION_DAYS: int = RETENTION_DEFAULTS["SCHEDULER_LOG_RETENTION_DAYS"]
    ENABLE_RAW_RESPONSE_STORAGE: bool = False
    LEGACY_TABLE_FALLBACK_ENABLED: bool = False
    COLLECTION_GUARD_ENABLED: bool = True
    COLLECTION_LOCK_BACKEND: str = "postgres"
    COLLECTION_BATCH_MODE: str = "time_window"
    MORNING_BATCH_ENABLED: bool = True
    NOON_BATCH_ENABLED: bool = True
    EVENING_BATCH_ENABLED: bool = True
    WEEKLY_BATCH_ENABLED: bool = True
    FRED_MIN_INTERVAL_MINUTES: int = 1440
    FX_MIN_INTERVAL_MINUTES: int = 360
    NEWS_MIN_INTERVAL_MINUTES: int = 360
    EQUITY_MIN_INTERVAL_MINUTES: int = 720
    FEDWATCH_MIN_INTERVAL_MINUTES: int = 720
    FOMC_MIN_INTERVAL_MINUTES: int = 10080
    CALENDAR_MIN_INTERVAL_MINUTES: int = 1440
    SNAPSHOT_MIN_INTERVAL_MINUTES: int = 180
    AI_DAILY_INSIGHT_ENABLED: bool = True
    AI_DAILY_INSIGHT_TIMEZONE: str = "Asia/Seoul"
    AI_DAILY_INSIGHT_TRIGGER_IN_MORNING_BATCH: bool = True
    AI_DAILY_INSIGHT_BACKFILL_TRIGGER_ENABLED: bool = True
    CALENDAR_FRED_ENABLED: bool = True
    CALENDAR_FRED_LOOKAHEAD_DAYS: int = 180
    CALENDAR_BLS_ENABLED: bool = True
    CALENDAR_BLS_ICS_URL: str = "https://www.bls.gov/schedule/news_release/bls.ics"
    YFINANCE_RETRIES: int = 2
    YFINANCE_TIMEOUT_SECONDS: int = 20
    YFINANCE_TZ_CACHE_DIR: str = "/tmp/py-yfinance"

    @field_validator(
        "COLLECTION_SUCCESS_LOG_RETENTION_DAYS",
        "COLLECTION_FAILURE_LOG_RETENTION_DAYS",
        "RAW_RESPONSE_RETENTION_DAYS",
        "DEBUG_LOG_RETENTION_DAYS",
        "SCHEDULER_LOG_RETENTION_DAYS",
        mode="before",
    )
    @classmethod
    def validate_retention_days(cls, value, info):
        default = RETENTION_DEFAULTS[info.field_name]
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return default
        return parsed if parsed > 0 else default

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
