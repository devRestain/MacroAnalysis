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
    SENTIMENT_BATCH_SIZE: int = 20
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
